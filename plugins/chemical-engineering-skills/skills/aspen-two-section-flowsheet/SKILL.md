---
name: aspen-two-section-flowsheet
description: "Review section boundaries, gas/liquid handoffs, solvent returns and equipment ownership from text or Aspen flowsheets. Define section contracts, validate cross-section streams and coordinate sectioned construction through aspen-plus-operations. Keep phase-split placement unresolved until current interfaces and receiving duties are known; historical case references require an exact family match."
---

# Aspen Two-Section Flowsheet

## 工作过程

先检查现有模型和最新项目决定，按反应、净化、溶剂循环或中间产品等工程边界划分工段，不按旧块编号机械分成两半。每个工段都要说明由谁提供入口、处理哪些反应与分离、拥有哪些循环，以及向下一工段交付什么组成、流量、温压和相态。

气送与液返先核对是否已是独立接口、现有分相位置及逐相状态；资料只有总流量时，
两相共线的适用性、分相设备的必要性和位置都保留未定。明确接收设备不允许夹液
等约束后再比较现有分相、分别交接或新增分离，不能把缺资料变成默认增设设备。

新拟工段边界、职责或跨段合同本身就是方法与范围决定，先按[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)执行 `source` 知识准备；没有图纸或模型时仍查询当前问题，工况缺口明确保留。仅复述或核对已有合同的文件身份不新增阶段事件。随后按合同逐段建立或修复模型，专业问题交塔、动力学或热泵模块，具体操作交操作模块；工况形成及接回后执行相应阶段检查。只有局部结果与跨段物流都成立，才逐段接回，最终返回合同、同版物流和证据，不把临时边界进料描述成已闭合的内部循环。

## Network Position

Upstream authority is `aspen-document-driven-flowsheet` plus the current
project authority files. This skill freezes section contracts and cross-section
stream obligations, then returns evidence to the process authority layer for
promotion or quarantine. It may ask `aspen-plus-operations` for mechanical
case/block/run/export work, but it must not choose project chemistry, kinetic
constants, final product claims, or historical case values without current
source evidence.

## Skill Coordination

This skill owns process boundaries, not Aspen card mechanics. Use it when a
connected Aspen draft needs to be split into two engineering sections, when an
existing two-section model has unclear cross-boundary streams, or when a project
needs section-specific acceptance gates before full-flow reconnect.

When the active project contains
`aspen_sun_lanyi_knowledge/knowledge_graph/README.md`, read that local overlay
before choosing reactor, separator, column, convergence, or analysis-tool
patterns. Use it for Aspen card routing and uncertainty handling, especially
`unknowns_router.md`, `classic_cases_playbook.md`, and
`kinetics_expert_system.md`. Keep this skill responsible for process
boundaries; do not let historical cases override newer project source documents
or turn example numbers into authority values.

For mechanical Aspen work, call `aspen-plus-operations` with:

```text
Operation goal:
Authority artifact:
Inputs and source units:
Allowed changes:
Required evidence:
Stop condition:
```

Typical operation routing:

- `case-io`: generate `.bkp/.apwz` from `.inp`, reopen, and export evidence.
- `block-stream`: add or reconnect section blocks and require exported
  `FLOWSHEET` lines.
- `reaction-card`, `equipment-card`, `calculator`, `design-spec`: set section
  cards only after the section contract defines the target and allowed changes.
- `run-export` and `delivery-qa`: run, export status/streams, and package final
  section cases.

## Core Rule

Do not treat every Aspen block as a field device. Build and explain the process
in engineering sections. A section may contain several Aspen implementation
blocks, but it must have one defensible process boundary, owned reactions and
separations, and explicit outlet obligations.

A connected draft is only a runnable material-balance draft until its section
boundaries are defensible.

## Section Contract

Before editing Aspen, write one contract per section:

```text
Section name:
Source basis:
Inlet boundary streams:
External makeup boundaries:
Owned reactions:
Owned separations:
Owned recycle loops:
Outlet products/intermediates:
Cross-section stream contracts:
Allowed placeholders:
Forbidden assumptions:
Acceptance gates:
Open blockers:
```

Cross-section stream contracts must state composition basis, flow basis,
temperature, pressure, phase expectation, quality target, recycle or product
destination, and whether the stream is a real internal recycle, a temporary
boundary, or a scaffold seed.

For a boundary review without a model, return these alternatives explicitly:

| Current evidence | Boundary decision |
| --- | --- |
| Gas delivery and liquid return are already separate interfaces | Verify their individual states, composition and equipment ownership; do not invent another shared two-phase pipe or separator. |
| A common two-phase line is evidenced and the receiver can accept its full operating envelope | Evaluate common transfer against phase equilibrium, pressure drop, holdup, controls and both phases' actual destinations. |
| A receiver requires dry gas or a liquid-only feed | Identify where existing equipment already meets that requirement; compare an added split only if a real unmet duty remains. |
| Interface arrangement, receiving duty or phase states are unknown | Keep common transfer, separate transfer and separation placement unresolved; identify the missing discriminator for each option. |

Different gas/liquid destinations require separate accounting, but do not by
themselves locate a new separator at the section boundary. The opening conclusion,
decision table and closing recommendation must retain the same unresolved branch;
do not announce a default placement and qualify it only afterward.

## Workflow

1. Inspect existing files before changing anything.
   List `.bkp`, `.apwz`, `.inp`, generation scripts, block/status CSVs, stream
   CSVs, audit Markdown, and current authority notes. Identify runnable Aspen
   cases versus reports, probes, stale branches, and rejected drafts.

2. Extract the section map from current source documents.
   Split by engineering boundary, not by historical block IDs. Good split points
   include product/intermediate boundaries, gas cleanup boundaries, solvent or
   entrainer loops, reactor train boundaries, utility/pressure islands, and
   sections that can be validated independently.

3. Freeze each section contract.
   The contract must define the section's inlet basis, outlet obligations,
   reactions, separations, recycles, external makeups, placeholders, and
   acceptance gates. If the source does not support a boundary stream or makeup,
   mark it `provisional` instead of hiding it as an internal recycle.

4. Choose the Aspen case strategy.
   Use separated Aspen cases when sections can run with explicit boundary
   streams and need independent validation. Use island cases when one reactor,
   tower train, cleanup loop, or recycle subsystem needs rigorous design before
   reconnect. Use one connected full-flow case only after section-local gates and
   cross-section stream contracts pass.

5. Build or repair one section at a time.
   Start with scaffold reactors/separators only when they are labeled as
   temporary process-balance devices. A `SEP` represents a separation duty or
   train, not one real device. Replace it later through the main
   `aspen-document-driven-flowsheet` scaffold/island workflow.

6. Validate section-local gates.
   Each section must run/reopen/export, have clean or explicitly quarantined
   block/calculator/spec status, and meet its own conversion, recovery, product,
   pressure, recycle, and terminal-stream gates.

7. Validate cross-section contracts.
   Check every stream that crosses sections against the contract. Do not let a
   section consume a hidden free raw material, silently discard a valuable
   intermediate, or return a contaminated recycle without a treatment/recovery
   boundary.

8. Reconnect only after section evidence passes.
   Reconnect one accepted section or island at a time. Preserve same-version
   backups, exported inputs, block/status CSVs, stream CSVs, and run summaries.
   If a reconnect fails, read Control Panel/history first and decide whether the
   issue is syntax, property method, feed inventory, pressure, recycle
   initialization, convergence setup, or an over-tight section target.

## Generic Validation Gates

A sectioned Aspen deliverable is not acceptable until:

- Every section has a written contract tied to current source evidence.
- Every separated case or retained island has `.bkp` and `.apwz` evidence when
  Aspen archive delivery is required.
- Every promoted case reopens from `.bkp` and exports current `.inp` evidence.
- The accepted run returns and the latest block/calculator/spec statuses in
  the authorized delivery scope are clean under the existing strict operation
  gates. Quarantined diagnostics remain unaccepted audit records; quarantine
  does not remove a required section or device from the promised coverage.
- Cross-section stream contracts match exported stream results.
- External makeup boundaries, purge/treatment streams, and recycle returns are
  explicit.
- Remaining placeholders are named as placeholders and not presented as final
  equipment.
- Historical case values, stream IDs, tower specs, and split fractions are not
  reused unless the current source independently authorizes them.

## Project resources

For the source-preserved section builder, first read
[the explicit profile contract](scripts/PROFILE_CONTRACT.md), then use
[build_two_section_corrected.py](scripts/build_two_section_corrected.py).
Its original 22 function identities and parameterization are mapped in
[SOURCE_PRESERVATION.json](scripts/SOURCE_PRESERVATION.json). Supply the current
project's own profile and exact SHA256, components, molecular weights and
reported field units; there are no historical project values by default.

The builder produces candidate input and a controlled handoff to the existing
operation template/runtime, not an Aspen run or an accepted model. Readback
gaps remain unknown instead of zero. The original unsafe run body is retained
as [audit-only source text](scripts/run_case.audit-only.txt), never executed.
The synthetic profile only tests serialization and boundary behavior; it is
not a flowsheet. No COM run was performed to qualify this restored route.
Freeze section contracts and cross-boundary evidence from current sources
before any separately authorized operation through `aspen-plus-operations`.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
