# 维护时的组织与观察工具

只在更新Skill、追踪文件改动影响或比较明确的运行记录时读取。普通化工任务继续走现有专业入口。
工具安装在 `{CHEM_WORKSPACE}/chemical-engineering-runtime/tools`；使用目标环境的已验证Python。
它们不增加MCP注册，不调用Aspen，不自动改规则或晋级经验。

## 文件组织和影响范围

```text
python -B -X utf8 "{CHEM_WORKSPACE}/chemical-engineering-runtime/tools/skill_organization.py" inventory --root <完整源码或发行目录>
python -B -X utf8 "{CHEM_WORKSPACE}/chemical-engineering-runtime/tools/skill_organization.py" impact --root <完整源码或发行目录> --changed <仓库相对文件路径>
```

完整目录中必须有产品的 `plugins/chemical-engineering-skills/skills`；运行时安装目录只含运行资产，
不能当完整源码。多个改动重复 `--changed`。工具只向标准输出返回JSON，调用方可保存到本次维护结果目录。

先看 `skills`、`coverage` 和 `issues`，再看带类型/行号的 `edges`、`unresolved_edges`。
影响查询给出反向引用候选、传播依据和相关Skill。**文件归属不是事实owner，静态引用不是调用证据**。
实际规则权威仍以 [owner表](CANONICAL_RULE_OWNERSHIP.md) 为准。
动态路径、运行时导入、复杂Markdown、JSON/COM语义、安装镜像和内层身份锁须另外核查；
未解析项不等于无依赖。修改消费者前复核实际路径/内容，不按影响集合自动批量改写。

## 明确证据清单的观察索引

```text
python -B -X utf8 "{CHEM_WORKSPACE}/chemical-engineering-runtime/tools/observation_index.py" --manifest <清单绝对路径> --evidence-root <证据根绝对路径>
```

清单schema为 `chemical-observation-manifest-v1`；必填 `experiment_id`、`case_family_id`、
`task_id`、`revision` 字符串，`scenario_kind`、`execution_mode` 和 `artifacts` 数组。
每个artifact显式给出根内相对 `path`、`role`、64位 `expected_sha256`；可增加有限字面身份指针
`expected_identity`，如 `/run_id`、`/identity/case_id`。完整模板和约束在发行目录
`docs/observation_index.md`，也可用工具 `--help` 核CLI入口。

场景区分 `normal/expected_refusal/injected_fault/natural_failure`；执行区分
`real_tool/offline_stub/text_only`。可列 `declared_resources` 和 `observed_resources`，
未观察填null或省略；显式空数组只是报告空集合。两者都是清单声明，不能当独立调用证据。

索引只读取列明文件并核对字节哈希，哈希变化时不解释其中状态。JSON身份按原类型比较，
冲突、缺失、未观察分别保留；0、false、null不互相替代。
工具返回0只表示索引完成，不表示文件完整或工程成功。原资格回执可被关联，但仍由
[严格准入规则](STRICT_ACCEPTANCE_AND_LEARNING.md)及原检查器判定。

## 进入实际更新

整理结构或比较组织方案时，按需查[论文机制与评估边界](SKILL_RESEARCH_APPLICATION.md)。
专业分组统一维护在[任务登记](ACTIVE_ASSET_REGISTRY.md)，不分别改写多份专业选择表。

1. 固定当前源、拟改文件和问题；仅查受影响范围，不要求每次加载全库。
2. 保留旧版，形成候选改动；已有等价规则优先复用，分类见[决策树](TASK_DECISION_TREES.md)。
3. 按实际行为和原工程规则验证；拒绝场景、离线替身、真实软件成绩分开。
4. 关联原始回执，记录缺口与否决原因；判断是否采用仍由当前维护范围及原owner负责。
5. 通过相应检查后密封和安装，记录旧文件备份、新增目标及安装回读；公开发布另按用户授权。

上述流程提供可检查的维护材料，不保证自动进化、全依赖覆盖或性能提升。
