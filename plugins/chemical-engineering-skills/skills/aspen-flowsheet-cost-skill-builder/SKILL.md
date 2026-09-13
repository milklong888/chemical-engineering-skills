---
name: aspen-flowsheet-cost-skill-builder
description: Map process descriptions or simulation block lists to physical non-reactor equipment and purchased-equipment scope, including package quotation boundaries, even without a BKP/INP. Also inspect new Aspen flowsheets, qualify cost sources, define sizing and purchased-cost recipes, and generate project-specific batch-analysis Skills. Use for block-to-procurement mapping, purchase counts, package cost coverage, or a new mother template and unfamiliar equipment family needing validated cost methods.
---

# Aspen Flowsheet Cost Skill Builder

## 工作过程

若当前只需把文字流程、块清单或报告摘录对应到实际采购设备，先实际读取
[设备映射规则](references/mapping-rules.md)，按其待核映射格式完成当前资料能支持的
物理项与采购边界判断。这个入口不以 BKP/INP 为前提，也不要求为了文字映射先生成
新 Skill、费用脚本或执行 Aspen。只有任务进一步要求建立或运行费用方法时，才进入
下方完整流程；设备尺寸与技术选型仍交给原专业负责人。

面对一个尚无适用费用方法的新流程，先读取当前导出，把模拟块对应到真实的非反应器设备，弄清哪些辅助设备属于同一套装置。随后按设备用途查找并核实原始费用来源，逐项固定尺寸变量、单位、适用范围、年份、币种、材料和压力修正，再生成这个项目专用的计算说明、脚本入口与审计表。

设备尺寸来自当前设备计算或经核验的同案结果，不能由费用曲线反过来凑数。来源锚点、边界、缺项和代表工况测试通过后，才把生成的项目Skill交给批量分析使用。没有随包费用数据时，先交付来源需求与方法草案，不制造费用总额；这项任务不自动触发共享经验学习。

## Purpose

Generate a new project-specific Skill with this fixed structure:

```text
mother template -> contained equipment -> how each item is sized and costed
                -> source evidence -> batch inputs -> audited outputs
```

The generated Skill is a draft until its mapping, formula sources, units,
validity ranges, and verification gates pass. Strict engineering values remain
unresolved when evidence is missing. This public package does not contain cost
CSV libraries or project recipes. A comparison layer may produce numbers only
after the user supplies the compatible, source-reviewed data and its replacement
contract; it must expose every replacement and uncertainty interval.

Read `references/external_cost_data.md` before invoking inventory, scaffolding
or data-dependent tests. Missing external data is `dependency_unavailable`, not
a calculated zero or permission to fill costs from memory.

## Safety And Scope

Work read-only against source Aspen files. Prefer exported text INP plus run
evidence CSV/JSON. If only a BKP exists, use a copied case and the documented
Aspen operations skill to export INP; do not parse or patch BKP internals.

Do not change Aspen/AEPA installation, registry, license, certificate, service,
DLL, or configuration. Do not bypass licensing. Do not modify the source case.
Exclude reactors from ordinary-equipment cost and keep utility OPEX separate.

## Workflow

1. **Define identity and boundary**
   - Record canonical BKP/INP paths and SHA256.
   - State the process boundary and whether utility-generation packages are
     inside it.
   - Keep mother identity separate from representative-run evidence.

2. **Inventory the flowsheet**

```powershell
python {CHEM_SKILLS}\aspen-flowsheet-cost-skill-builder\scripts\inventory_flowsheet.py `
  --template-id <template_id> --project-name <project_name> `
  --inp <absolute_exported.inp> --bkp <absolute_case.bkp> `
  --data-dir <user_reviewed_cost_csv_directory> `
  --out-dir <absolute_inventory_directory>
```

   Add `--utility-inp` for utility-authoritative parents and
   `--service-overrides` for reviewed physical mappings. Block type is only the
   first candidate; service semantics decide the equipment.

3. **Discover and qualify sources**
   - Read `references/source-discovery.md` in full.
   - Work through `source_request_register.csv` from highest authority downward.
   - Register exact page/table/formula, capacity basis, scope, year, currency,
     location, range, and local SHA256 in a source-evidence ledger.
   - Community pages may reveal terminology only. Final methods require the
     original official report, standard, vendor document, or primary paper.
   - Extract raw source anchors before fitting. Reproduce exact anchors and
     unit conversions with code.

4. **Review mapping and method contracts**
   - Read `references/mapping-rules.md`.
   - Resolve physical scope, subtype, material, pressure class, train count,
     sizing variables, and all package auxiliaries.
   - For a tower or package quote, explicitly inspect whether shell/internals,
     condenser, reboiler, reflux drum, pump, driver and controls are already
     included. Retain physical items in the inventory but charge included items
     only through their parent package. Unknown quote inclusions block totals.
     Record the executable coverage fields in `references/mapping-rules.md`.
   - A two-sided exchanger identifies one physical exchanger, not its subtype;
     do not infer shell-and-tube construction without equipment evidence.
   - Mark mapping as `reviewed` only after evidence supports it.
   - Require unique, nonempty equipment IDs and exact inventory/assignment
     coverage in both directions. Duplicate charge rows, missing assignments
     and unlisted items block both cost layers, including comparison mode.
   - Pair `UTILITY_OPEX` only with `utility_opex_separate`; exclusion scopes use
     `LOGICAL_OR_REACTOR_EXCLUSION`. Actual CAPEX candidates must satisfy the
     strict completeness and selection gates regardless of scope labels.
   - Leave specialized or unsupported equipment unresolved and add a source
     request; never borrow a generic vessel or the largest available cost.

5. **Audit sources**

```powershell
python {CHEM_SKILLS}\aspen-flowsheet-cost-skill-builder\scripts\audit_source_evidence.py `
  --assignments <equipment_method_assignment.csv> `
  --ledger <source_evidence_ledger.csv> --out <source_audit.json>
```

6. **Generate the specialized Skill**

```powershell
python {CHEM_SKILLS}\aspen-flowsheet-cost-skill-builder\scripts\scaffold_cost_skill.py `
  --inventory-dir <absolute_inventory_directory> `
  --data-dir <user_reviewed_cost_csv_directory> `
  --skill-name <lowercase-hyphen-name> `
  --skills-root <project-local-draft-skills-directory>
```

   Add `--require-ready` only after all mapping and source gates are approved.
   Without it, unresolved methods remain drafts. If no cost library is available,
   use `--draft-only` without `--data-dir` to create the executable framework and
   empty schemas; its runner records `blocked` and emits no cost numbers.
   Follow `references/no-data-draft.md` for the minimum evidence inventory.
   Reuse the bundled `run_recipe_batch.py`; do not invent a second batch runner
   that checks an `approved` flag. Its entry audits the actual source ledger,
   current original hashes, package coverage and comparison contract every run.
   Every cost-point `source_id` also requires a qualified original. Before either
   layer runs, the selected equipment/subtype/variant source group must belong
   to the assignment's declared source set; a verified source cannot endorse
   another source implicitly. Explicit qualified multi-source groups are allowed.

7. **Validate and forward-test**
   - Run `scripts/self_test.py --data-dir <reviewed_original_profile_csv_dir>`
     to check the original data profile's block-classification boundaries,
     source catalog coverage, exact NETL anchors, and range rejection. This is
     not a generic test of arbitrary new CSV datasets; absent data returns
     `dependency_unavailable`/exit 2 without running the data checks.
   - Run `quick_validate.py` on the generated Skill.
   - Run its method audit.
   - Test one exact source anchor, one interpolation interior point, each range
     boundary, one missing input, one invalid unit, and one representative case.
   - Test success then unresolved, and unresolved then success in the same
     manifest. Overall strict readiness requires every enabled case to pass;
     case order, a previous green audit or an `approved` label cannot relax it.
   - Run `scripts/test_cost_guards.py --work-dir <isolated_check_directory>` for
     source-identity, package-overlap, stale-audit and mixed-batch regressions.
     These synthetic software fixtures are not engineering cost validation.
   - Resume the same batch and require stable output hashes.
   - Compare to same-case AEPA item rows or an independent source when available.
   - Require every comparison row to have central/low/high values, a source,
     rule ID, tier, and a positive cost unless it is a documented structural
     exclusion or letdown boundary.

## Source Decision Rule

Accept a formula only when all are true:

- physical equipment and service match;
- purchased-equipment scope is explicit;
- capacity variable and units are explicit;
- base period, currency, location, material, and pressure basis are known;
- source table/formula can be independently reproduced;
- target case lies inside the supported range, or a separately reviewed
  extrapolation method exists;
- calibration is not silently reused outside its validated domain.

Otherwise keep `source_gap`, `method_gap`, or `validation_gap` open. The
generated Skill must expose the missing field and the next preferred source.

## References

- `references/source-discovery.md`: authority ladder, search queries, extraction,
  source upgrading, and rejection rules.
- `references/mapping-rules.md`: Aspen block-to-physical-equipment rules.
- `references/generated-skill-contract.md`: generated files, schemas, and ready
  criteria.
- `references/external_cost_data.md`: user-provided data directory, required
  schemas, readiness and unavailable states; data files are not bundled.
- `references/exploration-lessons.md`: why the workflow was generalized into
  separate mapping, sizing, base-cost, adjustment, and validation layers.
- `references/comparison-completion-schema.md`: deterministic IF rules for the
  non-null comparison layer and its uncertainty audit.

Any project-specific example is optional local evidence, not distributed here
and never a source of universal correction factors.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
