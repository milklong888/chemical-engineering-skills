---
name: sw6-scripted-equipment-design
description: "Coordinate narrow SW6 scripting work after equipment evidence has been routed: known-safe SW6 project-file field transfer, readback audits, and SW6 calculation-book evidence gates. Use only when the user explicitly asks for SW6 scripted input/readback, .fx3/.cn2/SW6 file mapping, automated transfer from Aspen/EDR/report ledgers into SW6 files, or SW6-result proof chains; defer general equipment-selection audits to chemical-equipment-selection-audit and Aspen model work to Aspen skills."
---

# SW6 Scripted Equipment Design

## 工作过程

只有任务明确要求SW6字段传递、文件回读或计算书核验时才进入本模块。先由设备审计确认同一设备的结构、设计条件、材料和证据等级，再核实目标SW6版本、模块以及用户提供的已验证字段映射，将能证明安全序列化的字段写入受控副本，并逐项回读比较单位、数值和文件身份。

未验证的材料、字符串或几何不猜偏移写入。最后用同一设备的SW6计算书核验正式结论，并把差异交回设备审计；没有映射程序或商业软件证据时，交付具体待补项和已完成的账本，不声称包内自带可运行的SW6引擎。

## Scope

This skill is a narrow implementation layer. It must not replace:

- `chemical-equipment-selection-audit` for equipment report reading, formula-family choice, parameter-source classification, or mismatch audits.
- Aspen skills for flowsheet/card/model work.
- PDF/DOCX skills for document extraction alone.
- Vendor-boundary routing for pumps, compressors, membranes, or catalog selections.

Use it only after the equipment identity and evidence route are clear, and the task specifically needs SW6 scripting, SW6 project-file field mapping, or SW6 calculation-book proof control.

## Required Preflight

Read the current equipment identity, source ledger, allowed edits and SW6
version/module before scripting. An optional local equipment graph under
`{CHEM_WORKSPACE}` may supply routing and software boundaries; its private
contents and automation scripts are not distributed here.

If the task is not SW6 file mapping/readback or calculation-book evidence,
route to the broader equipment/Aspen skill.

## Same-Case Mapping Gate

Use the current user's independently verified mapping and test artifacts.
Require a complete chain from same-equipment input through units and
serialization to readback and report comparison. Historical equipment IDs,
binary offsets and sample files are deliberately not supplied: one file's
offsets do not establish another version/module's layout.

The local user must provide the mapping runner/config and validation evidence.
If absent, return a concrete dependency/mapping gap; do not imply that this
instruction-only skill includes a working SW6 automation engine.

## Workflow

1. **Manual decision gate**: confirm equipment tag, family, SW6 module, calculation/check mode, structure type, pressure/diameter basis, material source, and evidence class.
2. **Ledger classification**: mark every value as `direct_reuse`, `method_only`, `software_boundary`, `vendor_boundary`, or `forbidden_transfer`.
3. **Script config**: create or update a project-local configuration for the exact equipment tag and SW6 module, with source/hash and mapping identity.
4. **Safe transfer only**: put confirmed binary fields in `fx3_mappings`; put uncertain strings/materials/geometry in `known_text_values` until serialization is proven.
5. **Run readback**: use the user's verified local runner for known-safe fields; keep all results bound to the same input, mapping version and SW6 artifact.
6. **Compare progressively**: each row must show source, formula/conversion, unit, script value, document value, tolerance, status, and evidence boundary.
7. **SW6 calculation-book gate**: do not claim formal tube-sheet, flange, nozzle reinforcement, skirt/support, or pass/fail results until an exported SW6 calculation book or screenshot is attached.
8. **Mismatch handling**: classify unit, mapping, serialization, authority or software-evidence conflicts before changing formulas or tolerances.

## Distribution Boundary

No project configs, binary field maps, proprietary SW6 files or local automation
implementation are bundled. Never patch materials or unmapped geometry before
same-version sample comparison or legitimate SW6 export proves serialization.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
