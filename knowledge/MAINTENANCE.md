# 新资料、候选与独立知识版本

日常查询不写库。本入口只把明确的新资料维护请求变成可验证的独立候选目录；
不覆盖活动知识，不自动发布，不把候选审查说成工程验收或模型训练。
原有6873条内容不会被重新摘要；新增用新ID，替代用新ID加supersedes，原正文、
原ID及来源保留，旧项仅退出默认检索。

## 两种输入分开走

- `direct_source`：用户明确增补外部资料，保留`X`来源知识。每条都要有来源ID、
  具体定位、文件SHA、原内容、单位/基准、层级、适用范围与许可范围。独立review
  精确覆盖整批变更SHA并逐条绑定正文、来源、层级和许可；不要求等待这个资料
  维护任务结束。程序核绑定和声明完整性，不替代人的来源核查或身份认证。
- `task_experience`：从任务结果提炼prompt_principle/data_pattern。每个节点另外
  提供各自的谱系manifest和候选质量review，复用现有中央关闭、谱系、规则绑定与
  质量门；一张root卡不能代替整批节点审查。缺门只保留待审记录。

放宽祖先一律不能进入默认检索。不能把任务产物重新标成external_source绕门。
来源文件和独立review证据本体还会经现有中央intrinsic检查；真实任务回执即使
严格通过，也必须走task_experience，不按文件名或“case”字样泛判普通教材。
中央helper、资格门、质量门及所需严格解析器先按
`learning_owner_contract.json`核定本产品文件SHA，再加载；显式skills-root
只选择安装位置，不能引入同名伪造门。
没有review时，仍保留可解析输入与明确缺口，但新增节点不进入records和向量。
来源或review身份漂移、重复ID、缺字段/许可、批次覆盖不完整等结构错误在输出前拒绝。

超过当前20MB结构化读取上限的JSON/JSONL来源或review证据保留为资源待审，
返回明确的`*_STRUCTURED_PAYLOAD_REVIEW_LIMIT`，不会因文件大就称其为任务经验或
放宽案例。可以提供保持原来源哈希/定位的受控分段审查输入，或由维护者另行核大文件。

## 实际入口

```text
python knowledge/scripts/build_knowledge_version.py --intake <intake.json> --inspect
python knowledge/scripts/build_knowledge_version.py --intake <intake.json> --review <review.json> --output <不存在且在本产品外的候选目录>
```

`--base`默认当前产品knowledge目录；不能借此引用另一个来源仓库的算法。
`--skills-root`可明确指定安装后的技能根，用于任务经验的现有中央门。
输出目录的父目录须存在；已有输出、当前产品或活动Skill内的输出均拒绝。
Windows未确认启用长路径时，会按实际文件全集分别预检最终路径和短暂存路径。
超限返回`WINDOWS_PATH_LIMIT_FINAL`或`WINDOWS_PATH_LIMIT_STAGING`、最长相对文件、
文件/目录长度限制和至少需要缩短的父路径长度；这不是来源缺失。请选用户可写的
短父目录，例如先准备`C:/ChemK`再输出到`C:/ChemK/candidate`。工具不修改系统开关、
不自动移动输出，也不删除长文件名的原脚本；暂存预检失败只清理自身空临时目录。
需要NumPy以调用原哈希向量构建器；原版依赖已在本产品离线轮子锁中。

输入结构见 [intake schema](schemas/knowledge_version_intake.schema.json) 和
[逐节点review schema](schemas/knowledge_intake_review.schema.json)。
一个变更含`operation=add|supersede`、`origin_kind`、显式
`relaxation_applied=false`、`record`、`source`和`license`。
`record`需含：`node_id/corpus/title/text/knowledge_layer/evidence_class=X/
authority_scope=shared/project_value_transfer_allowed=false/units_basis/
applicability/forbidden_transfer`。

运行`--inspect`得到`intake_sha256`与`changes_sha256`，每个decision列出
`change_sha256`；此时没有审查可返回退出码2并说明缺口，不写输出。
review使用不同的reviewer_id（与proposer_id分开），每项decision明确为
`admit_source_candidate`或`hold`，绑定source_sha256、text_sha256、knowledge_layer、
distribution_scope、核查basis与独立review证据文件的路径/SHA。
本工具不会只凭`approved=true`接受整批节点。

任务经验变更还需`experience.lineage_manifest`和`experience.candidate_review`
两个`{path,sha256}`引用。每条正文必须精确绑定其已准入root声明字段；
中央门不完备时，返回原门的缺口，不自建简化版进化审批。

## 输出与后续验证

候选目录包括`knowledge/`和运行检索必需的原`workspace/scripts/`字节副本，
不是第二完整产品，也不包含另两个仓库。`knowledge/VERSION_REVIEW.json`
记录逐项准入、基线与review身份；`candidate_intake.json`保留未准入原内容，
明确非默认检索/禁学习。构建先复制到任务临时目录，完成内层清单、向量、
全部来源重核及验证后才原子落到指定新目录；普通失败不留下半个可用库。

```text
python <候选目录>/knowledge/scripts/verify_knowledge.py
python <候选目录>/knowledge/scripts/query_knowledge.py --node-id <新ID> --full-text --json
python <候选目录>/knowledge/scripts/query_knowledge.py --query <关键词> --vector --json
```

只有此候选目录的查询会看到已准入新节点；活动库始终不变。即使全部节点准入，
状态也只是`candidate_release_review_only`，`canonical_write_authorized=false`、
`publication_authorized=false`、`engineering_acceptance_verified=false`。
`local_only`许可的材料不可作为公开发布资料；最终仍需主审按许可/技术边界
选择合格候选，并在独立发布版本中使用既有`tools/build_release.py seal`。
这个工具不提供自动晋升、覆盖安装或批量改用户项目的捷径。

因此完整顺序是：普通来源登记 → 逐节点独立审核 → 独立候选构建 → 用候选自身
查询/校验 → 主审决定是否纳入一个新的完整产品版本 → 既有发布工具封包和校验。
整包发布还需其余模块与依赖完整，不能直接把仅knowledge的候选目录称为完整产品。
