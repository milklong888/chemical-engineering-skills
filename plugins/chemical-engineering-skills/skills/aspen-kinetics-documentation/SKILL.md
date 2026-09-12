---
name: aspen-kinetics-documentation
description: Write source-faithful Aspen kinetics documentation from papers, ledgers, Aspen cards, and USER subroutines. Use when the user asks for 动力学说明, 来源文献, Aspen 输入参数, USER 子程序, 参数换算, reaction kinetics PDFs, or formal explanations of how literature kinetics are entered into Aspen.
---

# Aspen Kinetics Documentation

## 工作过程

从当前采用的论文、动力学账本、Aspen导出卡片和USER源码开始，逐个反应对齐原始速率式、参数出处、单位和反应基准，再把换算写到Aspen卡片或子程序实际接收的数值为止。需要USER时，继续核对组分顺序、REAL/INT参数、编译文件和加载方式，让读者能够从文献一路追到当前模型的真实输入。

缺口先通过原文定位、量纲和换算核查解决，仍缺必要依据的参数明确保留边界。正文不堆砌并未作为输入的演示速率，也不借说明书改动模型。若发现必须改反应表达式或参数，先交回流程负责人更新来源合同，再由操作模块实施；说明文件最后与同版卡片、源码和附件逐项核对。

## Core Rule

Write only to the parameter value that Aspen or the USER subroutine can actually receive.
Keep every source-to-input unit conversion with numbers.
Do not include operating-condition rate examples in the main explanation unless the calculated value is itself an Aspen input, a USER `REAL(i)`, an `INT(i)`, a hardcoded subroutine constant, or a required reactor geometry/catalyst-basis value used by the subroutine.

## Evidence Chain

For each reaction, freeze this chain before presenting it as formal:

```text
source equation/value -> source table/equation/page -> source units
-> required Aspen/USER basis -> unit conversion with numbers
-> exact Aspen card or USER parameter -> exported/card/subroutine verification
```

If any link is missing, label the item `candidate`, `provisional`, or `blocked`. Do not invent or silently borrow kinetic constants, adsorption terms, equilibrium constants, fugacity assumptions, catalyst bases, or component order.

## Required Reaction Entry

For every kinetic reaction, write these items in order:

1. Source literature title and role: main source, secondary closure, equilibrium closure, or runtime evidence.
2. Reaction and stoichiometry exactly as entered in Aspen.
3. Original rate equation and source location, including table/equation number.
4. Original parameters, original units, and source table/equation.
5. Unit conversion to Aspen/USER input parameters, with numeric arithmetic only until the input value is obtained.
6. Exact Aspen input: reaction set name, `SUBROUTINE`, `NREAL`, `NWORK`, `REAL VALUE-LIST`, phase, and `STOIC` order.
7. USER subroutine mapping: `REAL(i)`/`INT(i)` assignments, hardcoded constants, runtime unit normalization, and component identification logic.
8. Runtime connection: `.for`, compiled `.dll`, `.dlo`, `aspfiles.def`, and how Aspen finds the subroutine.

## Calculation Boundary

Keep:

- kJ/mol -> J/mol if the subroutine uses `R=8.314 J/(mol*K)`.
- J/kmol with `R=8314 J/(kmol*K)` when the source uses kmol basis.
- bar -> Pa only if the parameter or subroutine requires Pa.
- kmol/m3 <-> mol/m3 factors, such as `/1000` for adsorption constants when the source uses `m3/kmol` but the rate expression uses `mol/m3`.
- mol/(kgcat*s) -> kmol/(kgcat*s) and catalyst-loading multiplication only when the value is passed to Aspen as a rate or is explicitly used in USER code.
- Equilibrium constants such as `KP1`-`KP4` when hardcoded in the subroutine; show the source formula and numeric substitution.

Do not keep:

- Case-study inlet calculations of partial pressure, `k(T)`, or instantaneous rate if Aspen/USER calculates them at runtime.
- Demonstration rates such as `kmol/(m*s)` unless that exact value is entered or hardcoded.
- Literature operating cases as parameter evidence when they only validate behavior.

## Aspen/USER Special Checks

- USER component order is part of the model. If the subroutine identifies components by stoichiometric position, document the exact `STOIC` order and the failure mode if reversed.
- Native `POWERLAW` or `LHHW` may be used only if it preserves the source rate form exactly. Product inhibition, mixed fugacity/concentration bases, special denominators, or custom runtime normalization usually require USER.
- A `.bkp` alone is not USER kinetics evidence. Formal delivery needs source/subroutine files, loader files, compiled DLLs, and after-run exported cards showing the same `SUBROUTINE` and `VALUE-LIST`.

## Writing Style

State the relationship among papers simply: main kinetic source first, then secondary closure papers and why they are needed.
Use clear tables for `REAL VALUE-LIST` mapping.
Use concise code blocks for Aspen cards and subroutine excerpts.
When producing PDF/LaTeX, render-check the modified pages and revise if tables, formulas, or code blocks overflow.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
