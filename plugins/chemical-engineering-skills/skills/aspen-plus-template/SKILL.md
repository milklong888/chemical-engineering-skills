---
name: aspen-plus-template
description: Create and verify component-only Aspen Plus templates from a traceable component list through the existing COM conversion and roundtrip script. Use for component/CAS import and component-template BKP/APWZ requests; full flowsheets, towers, reactions and compression belong to their specialist skills.
---

# Aspen Plus Component Template

## 工作过程

先核实用户给出的组分名称、CAS、来源、目标数据库和Aspen版本，再把确认的组分表交给现有模板脚本，通过Aspen自身解析和导出生成文件。之后复开生成的模板，逐个比较导出的组分身份与原始清单，记录未匹配、额外或临时占位的组分，避免相似名称被误当作同一种物质。

这个模块只交付组分模板及读写核验证据，不为没有物流的模板虚构一次工艺运行，也不调用无关的设备选型。需要继续建反应、塔或完整流程时，带着已核实的组分清单交给流程模块，从对应阶段继续。

## Authority and scope

Read `references/ERROR_MEMORY.md` and the chemical expert's
`STRICT_ACCEPTANCE_AND_LEARNING.md`. This skill proves component identity and
template I/O, not process feasibility, kinetics, separation or equipment sizing.

A database lookup is evidence, not authority to substitute a similar chemical.
Failure to find an item in one local catalog does not prove Aspen lacks it:
use the available databanks/help/current component-source ledger before
declaring an unresolved identity. A labeled placeholder is a provisional
identity only, never a verified replacement.

## Short execution route

1. Freeze expected component IDs, CAS/source identities, property-method
   authority, source units, requested file formats and target Aspen version.
2. Use `scripts/create_aspen_template.py` with the supplied component CSV.
   Its CLI accepts `--csv`, `--out-dir`, `--stem`, optional `--title`,
   `--database-only` and `--with-dummy-flow`.
3. Let Aspen parse the text input and export its own archive. Use the common
   `aspen-plus-operations` runtime/lifecycle path; do not copy inline
   Dispatch/open/run/close code into another implementation.
4. Reopen the exact generated component archive and compare the exported
   COMPONENTS section against the frozen expected identities. Check hashes,
   size, actual version, missing/unexpected IDs and every placeholder.
5. Return template-specific states and evidence. No-flow component templates
   do not need an invented process run. If a test-only dummy flow is requested,
   label it as a fixture, not a customer process or reusable engineering value.

CSV fields consumed by the existing script:

`Component ID,CAS,中文名,English name,Formula/material,Aspen lookup/formula,Role,Status,Database verified,Note`

Example invocation shape (paths are supplied by the current task):

`python scripts/create_aspen_template.py --csv <source.csv> --out-dir <new-output> --stem <name> --database-only`

## Hard boundaries and routing

- Never hand-edit BKP/APWZ internals. Preserve required sidecars/layout and use
  the format-specific operation route.
- Explicit source units and property method are required; demonstration NRTL,
  pressure, split, efficiency and reaction values are not defaults.
- Never model pressure rise with a heater and call it a compressor. Full
  flowsheet/scaffold work routes to `aspen-document-driven-flowsheet`; card
  mechanics to `aspen-plus-operations`; tower work to its tower skill.
- Component verification is not strict full-flow delivery. For an actual
  process file, apply the current complete version-bound summary, raw-history,
  same-file, product and equipment gates through operations.
- Explicit user relaxation is case-only. Its artifacts and descendants cannot
  enter self-evolution, shared examples, default retrieval or general rules.

## Distribution scope

This release contains the component-template workflow, not historical process
exploration archives. Route full process construction to the current specialist
skill and use the current project's evidence rather than old numerical examples.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
