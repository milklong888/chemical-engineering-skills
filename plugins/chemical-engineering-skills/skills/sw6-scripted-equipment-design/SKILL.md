---
name: sw6-scripted-equipment-design
description: "Audit pressure-vessel project-file field mappings, version-dependent offsets, material/string serialization, and SW6 readback/report evidence. Use for SW6 scripted transfer, .fx3/.cn2 files, or vessel-file mapping risk reviews where the target software still needs identification. Confirm SW6 identity before SW6-specific execution; general equipment selection belongs to chemical-equipment-selection-audit."
---

# SW6 Scripted Equipment Design

## 工作过程

压力容器项目文件的字段、偏移或材料字节审查先确认生成软件、版本和模块；未给软件身份时，可以形成映射风险表，不推定文件就是SW6。确认SW6后，由设备审计核对同一设备的结构、设计条件、材料和证据等级，再审用户提供的已验证字段映射，将能证明安全序列化的字段写入受控副本，并逐项回读比较单位、数值和文件身份。

未验证的材料、字符串或几何不猜偏移写入。最后用同一设备的SW6计算书核验正式结论，并把差异交回设备审计；没有映射程序或商业软件证据时，交付具体待补项和已完成的账本，不声称包内自带可运行的SW6引擎。

## Scope

This skill is a narrow implementation layer. It must not replace:

- `chemical-equipment-selection-audit` for equipment report reading, formula-family choice, parameter-source classification, or mismatch audits.
- Aspen skills for flowsheet/card/model work.
- PDF/DOCX skills for document extraction alone.
- Vendor-boundary routing for pumps, compressors, membranes, or catalog selections.

For an initial vessel-file mapping review, keep software identity unresolved
until supported by the file or current task. SW6-specific implementation needs
clear equipment identity and evidence route; general equipment selection stays
with the audit skill.

## Required Preflight

Read the current equipment identity, source ledger, allowed edits and SW6
version/module before scripting. An optional local equipment graph under
`{CHEM_WORKSPACE}` may supply routing and software boundaries; its private
contents and automation scripts are not distributed here.

If the task does not concern vessel-file mapping/readback or SW6 calculation-book
evidence, route to the broader equipment/Aspen skill.

## Same-Case Mapping Gate

Use the current user's independently verified mapping and test artifacts.
Require a complete chain from same-equipment input through units and
serialization to readback and report comparison. Historical equipment IDs,
binary offsets and sample files are deliberately not supplied: one file's
offsets do not establish another version/module's layout.

A mapping risk table distinguishes numeric fields already proved on the exact
version/module from unverified numeric fields and from materials, strings and
geometry. Readable bytes, a matching offset, a valid checksum or a successful
save cannot establish engineering meaning. For each proposed safe field,
require a protected same-sample serialization comparison, independent readback
and agreement with the producing application's displayed/exported report value;
for SW6, use its same-equipment calculation report. Missing evidence keeps that
field unqualified and does not block a read-only risk table.

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
