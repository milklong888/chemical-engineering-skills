# 0.4.13：经验按职责合并与案例调用

作者：milklong（GitHub：milklong888）。本次按用户明确的 Skill 维护要求整理已有经验，不以离线检查宣称新的工程成功。

## 来源与范围

对照经验库[目录的固定版本](https://github.com/milklong888/chemical-engineering-experience-inbox/blob/03f436d3942086084a59ed6cfd9853f7c615ca55/priorities/catalog.json)中的八组内容。控制面板证据范围还参考了[独立提案的固定版本](https://github.com/milklong888/chemical-engineering-experience-inbox/blob/2a1d8ae00d1f2266268bf6d71f9b834bda45844f/proposals/EXP-20261017-verifiable-acceptance-and-closure.md)。后者仍保留原提案身份；此次合并不改变经验库的 PR、目录状态或未验证案例身份。源 Skill 基线为 `0c7187d260ae7b4f08cb9298753505bd16bbdfc3`。

原经验文字作者为 milklong888，许可为 CC BY 4.0；代码依原目录许可。本次新增文字为有范围限制的方法导航、指令和来源说明，未搬入项目模型或未经验证的工程结果。

## 合并位置

每个主题保留一个正文维护位置，Skill 入口只放触发条件和链接。已经具备等效规则的项目保留原文，不再增加同义副本。

| 经验条目 | 处理 | 负责位置与触发时机 |
| --- | --- | --- |
| EXP-20261022-knowledge-escalation-p0 | 合并 | [检索升级](../plugins/chemical-engineering-skills/skills/chemical-engineering-expert/references/KNOWLEDGE_LOOKUP_ESCALATION.md)：当前知识不足、未知警告或拟采用未核实值时，按已有层级查来源；本机已有正文同步到公开源，四个入口按需调用。 |
| EXP-20261012-user-required-guards | 已有项保留，补缺 | 设计、物性、参数权威、资源和文件身份继续归原模块；[分项证据](../plugins/chemical-engineering-skills/skills/chemical-engineering-expert/references/STRICT_ACCEPTANCE_AND_LEARNING.md)补控制面板缺口边界；[试算组织](../plugins/chemical-engineering-skills/skills/aspen-document-driven-flowsheet/references/aspen_convergence_trials.md#branch-control)补用户预算及显眼待更新项。 |
| EXP-20261012-operating-techniques | 去重与小量合并 | 复用桥接、UTF-8、复制核验继续归操作模块；整体流程、回流用途与图文分工进入[工程表达](../plugins/chemical-engineering-skills/skills/chemical-engineering-expert/references/ENGINEERING_PRESENTATION.md)。 |
| EXP-20261012-aspen-evidence-parser | 复用，代码不变 | 继续使用操作模块已有 `aspen_evidence.py`，不复制第二份、不用零填充未知计数。 |
| EXP-20261013-local-artifact-delivery | 有条件的工具参考 | 仅当文件已存在而客户端链接确实失败时，从工程表达页访问既有工具；不默认开服务。 |
| EXP-20261022-offline-audit-reference-tools | 保留隔离 | 原归档仍是审计参考，未接入默认检索，未晋升为成功案例。 |
| EXP-20261022-convergence-diagnostics | 案例/方法参考 | [收敛诊断案例](../plugins/chemical-engineering-skills/skills/aspen-flowsheet-error-repair/references/cases/convergence_diagnostics.md)：多设置耦合、残差平台、保存解与冷启动差异时读取。包含适用边界、反例和证据要求，不设默认参数。 |
| EXP-20261022-acm-membrane-product-methods | 案例与表达职责分开 | [膜建模案例](../plugins/chemical-engineering-skills/skills/aspen-document-driven-flowsheet/references/cases/acm_membrane_modeling.md)负责材料、量定义与模型交接；工程表达页负责图文与包内文件一致性。具体方程和数值仍须核原文。 |

完整触发路由见[任务决策树](../plugins/chemical-engineering-skills/skills/chemical-engineering-expert/references/TASK_DECISION_TREES.md)，职责划分见[规则维护位置](../plugins/chemical-engineering-skills/skills/chemical-engineering-expert/references/CANONICAL_RULE_OWNERSHIP.md)。

## 控制面板与收敛技巧的明确边界

- 为局部结论不必通读所有无关进度消息；但宣称整次运行没有实际问题，仍需同次完整消息捕获和扫描证据。
- 完整 Summary 未取得时，汇总计数保持未知。已经具备当前运行身份、有效上游和充分依据的产品等项目可以独立判断；不能补零、用旧结果替代当前结果或宣称整体严格通过。实际错误、警告和可辨非零仍需处理。
- 需要完整 Summary 的交付合同仍保留这项要求；局部缺口只阻断相应结论，不阻断其他可做工作。
- 收敛方法只提供待验证假设和对照思路。原文关于改变内层容差的讨论与当前精度锁冲突，已显式隔离，不进入默认建议。迭代预算不等于修改容差的授权。
- Aspen 的 PFD 排版按既有绘图 Skill 的 `image_layout_only` 接口调用前段，检查图块后返回 Aspen；完整 CAD 图纸走另一项明确任务。

## 本轮验证的范围

- 原证据解析相关回归：34 项通过；另用实际原解析器核验完整零表、显式非零、缺表和缺行四种输入。
- 新增本地链接与六个 Skill 入口结构分别在源树及安装树检查；原有工程执行代码保持不变。两处已有操作工作流相对链接也已修正。
- GPT-6 Luna 对四个合成场景独立阅读 Skill 后作规划：缺 Summary 但有有效产品证据、真实错误加陈旧结果、冻结容差的收敛诊断、膜建模与图文分工。主审确认关键范围判断与案例调用符合此次改动；没有执行 Aspen、ACM 或 ImageGen。
- 独立内容审查发现试算预算条款缺失，随后补入原维护位置。以上证据支持文档与路由维护，不证明收敛提速、模型准确性或真实项目验收通过。

本机更新采取定向增量，保留原有本机专用入口和路径；公开源与本机不做整树相互覆盖。
