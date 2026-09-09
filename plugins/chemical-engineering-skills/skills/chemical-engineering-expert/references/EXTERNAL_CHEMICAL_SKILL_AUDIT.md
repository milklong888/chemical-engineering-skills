# External Chemical-Engineering Skill Audit

Checked 2026-07-17. This file records why public Skill/Agent packages were
adopted, adapted, or rejected. A repository name, large file count, role title,
or permissive license is not evidence that its engineering content is correct.

## Audit rule

Evaluate each source on six independent dimensions:

1. provenance and license;
2. domain coverage;
3. field-level sources and applicability limits;
4. deterministic calculations or real tool execution;
5. hard failure gates and adversarial evaluation;
6. project-value isolation and rollback.

Only an independently verified mechanism may enter the canonical expert layer.
All example values and case-specific decisions remain external `X` or forbidden
transfer `F` until verified for the active project.

## Findings

| Source | What exists | Useful transfer | Why it is not a canonical chemical expert | Decision |
| --- | --- | --- | --- | --- |
| [a5c-ai/babysitter chemical-engineering package](https://github.com/a5c-ai/babysitter/tree/main/library/specializations/domains/science/chemical-engineering) | A broad MIT-licensed taxonomy of chemical roles, agents, skills, and JS workflows covering balances, thermodynamics, Aspen, equipment, reactors, separations, safety, control, economics, and documents | Stage orchestration, structured artifacts, checkpoints, logs, and a completeness inventory | Core skills such as [material balance](https://github.com/a5c-ai/babysitter/blob/main/library/specializations/domains/science/chemical-engineering/skills/material-balance-calculator/SKILL.md) and [thermodynamic selection](https://github.com/a5c-ai/babysitter/blob/main/library/specializations/domains/science/chemical-engineering/skills/thermodynamic-model-selector/SKILL.md) are capability lists without equations, applicability ranges, verified scripts, or field-level sources. The [process-development agent](https://github.com/a5c-ai/babysitter/blob/main/library/specializations/domains/science/chemical-engineering/agents/process-development-engineer/AGENT.md) emphasizes convergence and sizing but lacks non-compensable physical, topology, safety, and evidence gates | `adapt_architecture_only`; do not install as engineering authority |
| [theneoai/awesome-skills chemical-process-engineer](https://github.com/theneoai/awesome-skills/tree/main/skills/persona/manufacturing/chemical-process-engineer) | A persona/methodology prompt pack with broad questions about thermodynamics, safety, scale, heat integration, regulation, and economics | A small set of high-level review questions and anti-pattern reminders | Invented career credentials, unsupported universal percentages/margins, generic consultant prose, and software-development template leakage. Its license adds an attribution requirement beyond standard MIT; copying text would require those terms | `quarantined_for_facts`; independently restate only source-verified mechanisms |
| [jkitchin/skillz IDAES skill](https://github.com/jkitchin/skillz/tree/main/skills/programming/idaes) | An MIT-licensed, extensive tool-use guide for IDAES flowsheets, properties, initialization, diagnostics, optimization, costing, and dynamics | Progressive-disclosure routing and the habit of checking degrees of freedom, units, scaling, initialization, and diagnostics | It is a secondary tool adapter, not a macro process-design oracle. API examples and comparative claims may age or differ from official IDAES releases; it does not establish project property methods, route choices, safety, or economics | `reference_candidate`; current [official IDAES documentation](https://idaes-pse.readthedocs.io/) wins |
| [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | A large MIT-licensed collection of scientific package/database/research skills; chemical-process examples compose generic math, optimization, ML, and writing tools | Claim–evidence matching, uncertainty, alternative explanations, reproducibility, tool-specific routing, and security scanning | No verified full chemical-process-design expert, Aspen implementation layer, property-method authority, or plantwide topology rubric was found. Generic scientific evidence taxonomies do not replace engineering authority classes | `adapt_review_mechanisms_only` |
| [ChemCrow](https://github.com/ur-whitelab/chemcrow-public), [Coscientist](https://github.com/gomesgroup/coscientist), [AutoLabs](https://github.com/pnnl/AutoLabs) | Research agents grounded in typed tools, documentation, Python, and/or experiment execution | Route calculations to deterministic tools, keep action/observation traces, validate tool parameters, and use external review | Chemistry/lab scope is narrower than full process design; public repos do not reproduce every paper result; LLM self-judging is insufficient for chemical correctness | `promote_abstract_tool_grounding` through `EXTERNAL_AGENT_RESEARCH.md` |
| [IDAES](https://github.com/IDAES/idaes-pse), [DWSIM](https://github.com/DanWBR/dwsim), [BioSTEAM](https://github.com/BioSTEAMDevelopmentGroup/biosteam), and [ThermoSTEAM](https://github.com/BioSTEAMDevelopmentGroup/thermosteam) | Open process-modeling implementations with property, balance, recycle, diagnostics, optimization, or uncertainty capabilities | Structural/numerical diagnostics, independent checks, explicit recycle convergence, uncertainty/sensitivity, and transparent equations where applicable | Software success is still not project truth. Licenses differ, version-specific APIs change, and examples/parameters cannot be transferred across cases | `tool_or_independent_check`; use the exact version and same-case evidence |

## Why the largest public package is still shallow

The a5c package is useful as a coverage checklist because its overview includes
the expected professional domains and lifecycle. Its actual canonical skill
files, however, often contain only:

- a purpose sentence;
- a capability list;
- prerequisites and broad best practices;
- a configuration sketch;
- expected output artifact names.

That structure can tell an agent *what topics exist*. It cannot determine
whether a material balance closes, a property method is applicable, a recycle
accumulates an inert, a heat match is feasible, an Aspen field is correct, a
relief basis is adequate, or a flowsheet sequence is superior. Installing all
of those files would increase trigger competition and context without adding a
reliable engineering oracle.

## Mechanisms adopted locally

The local expert independently implements only these defensible mechanisms:

- one macro design authority above simulator/document implementation;
- non-compensable physics, safety, legal, and project-authority gates;
- a function-first flowsheet topology and component-fate audit;
- evidence classes and derivation-before-missing;
- deterministic calculations and same-case software/test evidence;
- candidate-only external knowledge intake with license/provenance boundaries;
- error memory promoted by user/source/test evidence, not self-confidence;
- route-aware retrieval with hard project-scope filters;
- blind/fresh-context evaluation and rollback before skill promotion.

## Content explicitly rejected

Do not internalize:

- invented expert biographies, certifications, plants led, or years of experience;
- universal operating margins, scale-up factors, flooding fractions, fouling
  multipliers, materials compatibility, relief values, savings percentages, or
  economic thresholds without applicable authority;
- example property methods, interaction parameters, kinetics, tower settings,
  equipment sizes, recycle ratios, heat-pump lifts, or product targets;
- “converged”, schema-valid JSON, or an LLM approval as proof of engineering
  correctness;
- broad bibliographies that do not support the exact claim, version, and scope;
- automatic write-back from generated summaries into a canonical skill.

## Installation decision

Do not install an additional external “chemical expert” package by default.
Retain `chemical-engineering-expert` as the single dispatcher, reuse the
workspace’s deeper Aspen/equipment/graph skills, and ingest an external source
only when it fills a named gap and passes the workflow in
`KNOWLEDGE_DISTILLATION_PIPELINE.md`.
