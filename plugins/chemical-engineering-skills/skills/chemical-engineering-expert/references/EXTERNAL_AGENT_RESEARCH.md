# Public Chemical-Agent Mechanisms Reviewed

Reviewed 2026-07-17. This is a provenance ledger for independently implemented
mechanisms. It is not a prompt collection, and no external project value,
closed prompt, figure, dataset, or code is copied into this skill.

## Findings

No reviewed system is a transferable full-stack chemical-process-design
expert. The useful material is architectural: role separation, tool-grounded
calculation, simulator feedback, whole-system evaluation, and governed memory.

| System and primary source | Verified mechanism | Independently adopted idea | Boundary |
| --- | --- | --- | --- |
| [AutoLabs paper](https://www.nature.com/articles/s41598-026-45593-z), [PNNL repository](https://github.com/pnnl/autolabs) | Supervisor separates clarification, chemical calculation, vessel/layout work, processing steps, and final orchestration; numerical work uses tools; guided self-checks target known error types; deterministic code emits strict hardware files | Separate understanding, calculation, engineering orchestration, implementation, and checking; attach a detector to each recurring error class | Validated on a narrow liquid-handling platform; human review remains necessary. Repository license must govern any code reuse |
| [From Text to Simulation, AAAI-26](https://ojs.aaai.org/index.php/AAAI/article/view/40215) | Task understanding, topology generation, parameter configuration, and simulator evaluation are distinct; evaluation includes economic, environmental, safety, technical, and topological dimensions | Freeze topology before parameters; require multi-dimensional whole-system review rather than convergence alone | Specific simulation environment; abstract mechanism only, no prompt/text reuse |
| [Context is all you need](https://arxiv.org/abs/2603.12813) | Process-development reasoning is separated from simulation-model implementation; balances and phase/equilibrium reasoning precede code | Maintain a design contract that the implementation layer cannot silently alter | Preprint and closed/custom implementation; complex phase behavior still needs domain evidence |
| [Aspen reasoning-agent paper](https://www.nature.com/articles/s44172-025-00583-3.pdf), [Aspen-AI repository](https://github.com/TSH-AI/Aspen-AI) | Source-prioritized retrieval, externalized intermediate evidence, progression from shortcut to rigorous models, and target-based material-balance derivation | “Not written verbatim” does not mean unavailable; calculate auditable balances and move from simple feasibility to rigorous verification | Representative distillation cases, not a general process-design proof; paper license limits derivative redistribution, so only abstract mechanisms are used |
| [ChemCrow paper](https://www.nature.com/articles/s42256-024-00832-8), [public repository](https://github.com/ur-whitelab/chemcrow-public) | Explicit expert-tool routing, literature search ahead of generic web search, Python calculation, human escalation, and hazard checks; expert review catches issues language-model judging misses | Route facts to sources, numbers to calculators, risk to hard gates, and genuine ambiguity to the user | Public repository omits some paper tools and cannot reproduce the complete study |
| [Coscientist paper](https://www.nature.com/articles/s41586-023-06792-0), [repository](https://github.com/gomesgroup/coscientist) | Planner actions are constrained to search, Python, documentation, and experiment; documentation precedes hardware code; results feed the next plan | Label each action as retrieval, calculation, documentation, or execution; feed verified output back to design | Public code is a simplified implementation; repository terms include commercial-use restrictions |
| [ChemAgent paper](https://proceedings.iclr.cc/paper_files/paper/2025/hash/fa7f64b45970e6a7f8824781e7e01501-Abstract-Conference.html), [repository](https://github.com/gersteinlab/ChemAgent) | Separates plan, execution, and task knowledge memory; decomposes work; evaluates/refines subtasks; reports harm from wrong or excessive memory | Separate procedural errors, validated reusable knowledge, and task-local facts; promote only externally verified items | Tested on textbook chemistry questions; synthetic memory from model parameters is prohibited for source-constrained projects; repository license must be checked before reuse |
| [Reflexion paper](https://papers.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html), [repository](https://github.com/noahshinn/reflexion) | External evaluation produces short episodic lessons; false-positive evaluators can pollute memory | Store compact detector/repair rules only after user, source, software, or test evidence | General agent work, not chemical engineering; evaluator quality controls memory quality |
| [CACTUS paper](https://arxiv.org/abs/2405.00972), [PNNL repository](https://github.com/pnnl/cactus) | Narrow chemistry tools have explicit descriptions and per-tool benchmark evaluation | Give each skill/tool an applicability contract and regression cases | Molecular/SMILES tasks, not process design; only the evaluation pattern transfers |

## Resulting local design choices

1. Keep the global prompt short and make it an unskippable dispatcher.
2. Separate design authority from simulator/document implementation.
3. Use evidence classes rather than a binary “in document/not in document”.
4. Require deterministic derivation before declaring missing information.
5. Evaluate the complete process across conservation, thermodynamics,
   topology, operability, safety/environment, and economics.
6. Keep error memory compact, scoped, weighted, and externally verified.
7. Quarantine new knowledge before promotion and preserve license/source
   boundaries.

