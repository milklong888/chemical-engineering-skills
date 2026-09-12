# 后置候选审查的最小数据合同

只在EVOLUTION_LOOP规定的用户发起正式整理且当前任务明确结束后读取。
临时经验收件按[独立收件导航](EXPERIENCE_INBOX.md)办理，不填本晋升合同替代收件。
普通任务微调不需要填此表。
现有self_evolve_skill.py和脚本复用入口的`--candidate-review`调用同一中央
`assess_evolution_candidate.py`；它不执行输入代码、不写Skill、不替代人工主审。

所有文件引用统一为`{path, sha256}`；相对路径对各JSON所在目录解析。重命名、
路径相同或时间戳相近不能代替哈希身份。

## proposal：chemical-evolution-review-v1

- `learning_channel`：prompt_principle或data_pattern，须与已关闭任务谱系一致。
- `candidate`：被谱系准入的根JSON提案，须包含相同learning_channel和rule_card；
  不是拿另一条已通过的规则替本条背书。
- `baseline`：当前实际owner文件；`rollback_snapshot`：该文件的独立精确快照。
- `placement`：唯一owner、实际target_path和仍存在的anchor。
- `rule_card`：trigger、observation、mechanism、action、verification、boundary、
  decision_change；valid_for/invalid_for为非空文字列表；knowledge_layer=L3/L2/L1；
  claim_type=behavior/deterministic_method/engineering_heuristic/software_rule。
  prompt_principle必须是L3且明确改变哪种宏观判断，参数/局部窍门不得混入。
- `comparison`：decision（no_change/merge/specialize/replace/add/retract等）、reason、
  实际existing_refs；不是用文本相似度自动判知识等价。
- `evaluation_plan`、`evaluation_result`：如下；缺失时输出needs_validation和
  具体补全项，不声称已经验证、不冻结无关工程工作。

## plan：evolution-evaluation-plan-v1

- baseline_sha256；basis文件引用（method/boundary/goal/tolerance/version，必要时
  analysis_target=simulator_convergence）；required_dimensions。
- development_case_ids；cases列表，每项id/split/dimensions/input/oracle。
- 有未参与开发的holdout，案例ID不重复、覆盖当前冻结维度；样本量按实际风险
  与覆盖要求决定，不能用重命名开发案例冒充留出测试。
- basis、输入和oracle在候选评测之前冻结；主审须核查作者与评测者的信息隔离，
  文件哈希本身不证明从未泄露答案。

## report：evolution-evaluation-result-v1

- plan_sha256、baseline_sha256、candidate_sha256；cases必须正好覆盖计划。
- 每项id/input_sha256/oracle_sha256，以及baseline_observation、candidate_observation引用。
- observation为evolution-observation-v1：case_id/input_sha256/basis_sha256/
  subject_sha256/raw_evidence/values。subject分别绑定基线或候选；values必须与
  原始JSON输出/已核验抽取的values_pointer（默认/values）一致，不只核文件存在。
- 文本/CSV/软件日志先走现有同案导出与有依据抽取，保留其原始来源链。这里的
  短JSON不是原始证据替代品。

## oracle：evolution-json-oracle-v1

hard_requirements是一组`{pointer, op, expected}`，支持eq/ne/gte/lte/finite/contains，
指向实际`/values/`数值或行动类别。不能只有passed/ok/success等自评布尔字段。
可选metrics为`{pointer,direction: lower|higher}`，例如同基准迭代数、稳定可行率、
明确目标函数或实际重复加载数量。最低发布审查要求是全硬门成立且有可观察增量；
本工具不自动批准指标权衡，出现退化交人工按事先合同判断，不悄悄改权重。

输出区分audit_only、needs_review_fields、needs_validation、not_improved和
ready_for_manual_review。后者仍`canonical_write_authorized=false`，不是已经
晋升；对机理、来源真实性、经验范围、版本和规则落位还要主审。
