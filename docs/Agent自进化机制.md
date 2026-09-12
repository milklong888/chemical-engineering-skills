# 化工设计专家工作库 0.4.6 发布

2026 年 9 月 12 日

化工设计专家工作库 0.4.6 现已发布。新版将主动经验提醒接入全部 19 项 Skill，并整合了任务协作、经验审核和规则维护的相关更新。

本次更新围绕 Agent 的工具使用和经验积累展开：任务结束一个阶段后，助手可以整理有复用价值的方法；后续维护时，再通过证据审核和测试决定是否将其纳入正式规则。

完整版本已在 [GitHub Releases](https://github.com/milklong888/chemical-engineering-skills/releases/tag/v0.4.6) 提供，支持本地命令行和可选 MCP 接口。

## 主动经验提醒

19 项 Skill 的阶段收尾规则现已加入经验提醒。助手需要展示具体的方法摘要、适用条件和投稿入口，方便使用者判断是否值得保留和分享。

已经执行的方法按实际版本和运行证据审核；思想原则先确认具体内容，再由助手审核。已有授权在其范围内继续适用，使用者拒绝或撤回后停止相应提醒和提交。多个子代理的候选由主助手统一整理。

愿意分享的使用者可以按[中文投稿指南](https://github.com/milklong888/chemical-engineering-experience-inbox/blob/main/docs/USER_SUBMISSION_GUIDE.zh-CN.md)提交候选 PR。安装 Skill 不会自动上传项目资料。

## 经验整理与版本维护

新版明确区分临时收件和正式规则更新。证据与公开授权齐全的候选可以先进入临时经验库；正式采用时，由用户发起整理并确认相关任务版本已完成，再核对已有规则、适用范围和反例，由维护者决定是否采用。

维护流程支持合并、细化、替换或撤回已有条目。同一规则统一维护，更新时保留版本和回退记录，便于处理重复内容及不同入口之间的冲突。相关工具检查材料和条件，内容是否采用由维护者复核。

本库的自进化主要通过提示规则、工具调用流程和外部记忆的维护实现，基础模型权重保持固定。具体流程见[经验管理与正式晋升说明](../plugins/chemical-engineering-skills/skills/chemical-engineering-expert/references/EVOLUTION_LOOP.md)。

## 任务协作与按需调用

本版整理了 19 项 Skill 的任务入口、职责和交接关系。Agent 可以按当前任务定位主要模块，再按需读取操作方法、调用工具并检查结果。

决策树补充了任务选择和排错分支；文件引用与影响索引用于维护时定位相关模块；观察索引用于核对显式列出的运行记录。这些入口覆盖了工具选择、知识查询、结果核验和经验整理之间的交接。

相关入口见[任务与协作索引](../plugins/chemical-engineering-skills/skills/chemical-engineering-expert/references/ACTIVE_ASSET_REGISTRY.md)和[维护工具说明](../plugins/chemical-engineering-skills/skills/chemical-engineering-expert/references/MAINTENANCE_TOOLS.md)。

## 测试结果

我们使用 Luna 对功能触发、跨模块选择和经验准入进行了检查，并为新增的提醒规则安排了单独复测。

| 测试 | 版本与范围 | 结果 |
|---|---|---|
| 100 个独立任务 | 固定 0.4.5；50 个功能、25 个跨模块选择与纠错、25 个经验准入 | 77 个完整通过，23 个部分通过 |
| 8 个经验提醒任务 | 0.4.6；同题三轮开发复测，显式提供 Skill 入口 | 末轮 5 个完整通过，3 个部分通过 |

提醒复测仍发现了遗漏投稿链接、声称草稿完成却未展示产物的情况。100 个任务中也有工具结果解释和审核步骤不完整的问题，这些均按部分通过记录。

两组测试用途不同，不能直接据此计算版本提升幅度。100 个任务中的部分题曾用于预运行，准入与提醒场景包含合成材料；8 题复测不属于独立留出测试，也不验证隐式 Skill 发现。目前还没有长期持续提效的对照结果。

此外，0.4.5 维护基线的 84 项检查中，82 项通过、2 项因缺少指定外部证据而跳过；独立经验收件工具的 69 项检查通过。本次发布不新增真实 Aspen、EDR 或 SW6 模型验收结论。

## 研究参考

相关设计参考了 [Reflexion](https://papers.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html) 的反馈反思、[ExpeL](https://arxiv.org/abs/2308.10144v2) 的经验整理、[Voyager](https://arxiv.org/abs/2305.16291v2) 的能力积累与检索，以及 [ACE](https://arxiv.org/abs/2510.04618v1) 的上下文局部更新。论文机制用于指导设计，实际采用范围和验证结果以本库记录为准。详细对应见[研究机制与采用边界](../plugins/chemical-engineering-skills/skills/chemical-engineering-expert/references/SKILL_RESEARCH_APPLICATION.md)。

## 使用与更新

请从[发行页](https://github.com/milklong888/chemical-engineering-skills/releases/tag/v0.4.6)下载完整离线包，按[使用手册](使用手册.md)校验并安装。已有使用者也需要重新安装，拉取源码不会自动更新本机已安装的 Skill。

离线依赖面向 Windows AMD64、CPython 3.14。实际 Aspen Plus、EDR 和 SW6 操作需要相应软件、许可及适配环境；原生 Sensitivity 的目标接口资格核验仍待完成。
