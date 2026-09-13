# 化工设计专家工作库

面向化工设计与 Aspen Plus 自动化任务的工作流和工具集合，包含 **19 个 Skill**、本地知识检索、设备计算程序，以及命令行和可选 MCP 接口。支持从设计资料或已有模型出发，组织流程构建、计算、修改、复核和成果交付。

使用时可以提供任务书、设计基准、参数表、运行记录或现有 Aspen 文件。系统按当前问题选择相关模块，提取输入、查询适用方法、调用工具，并记录计算结果、依据与未完成项。

[下载发行包](https://github.com/milklong888/chemical-engineering-skills/releases) · [使用手册](docs/使用手册.md) · [19 个模块说明](docs/模块说明.md) · [任务入口与协作图](plugins/chemical-engineering-skills/skills/chemical-engineering-expert/references/ACTIVE_ASSET_REGISTRY.md)

## 功能范围

| 功能 | 支持的工作 |
|---|---|
| 流程构建与整合 | 整理设计基准、组分和物性要求；建立流程骨架；划分反应、分离和循环工段；逐段完善模型并接回全流程。 |
| 模型操作与排错 | 组织 Aspen 文件读写、组分模板、单元与物流设置、计算及导出；根据当前日志和结果定位输入、物性、循环、控制或产品指标问题。 |
| 分离与能量优化 | 组织精馏和溶剂回收计算、热泵精馏改造、压力路径检查及热量安排；在明确的产量、质量和设备约束下比较方案。 |
| 设备计算与校核 | 由工况推导设备参数，执行适用的选型和校核；衔接塔水力学、EDR 换热器计算及 SW6 数据交接；将设备限制反馈到流程修改。 |
| 成本与工程文档 | 组织非反应器设备购置费分析、设备表、动力学参数说明、计算依据、流程图和报告修订，并记录数据来源与适用范围。 |
| 知识检索与经验管理 | 按问题查询分层方法、公式和设备事实；使用决策树定位任务分支；检查文件引用与改动影响；整理经确认、审核和授权的经验候选。 |

各模块的输入、依赖和交接范围见[模块说明](docs/模块说明.md)。费用分析、特定设备映射和商业软件计算需要相应数据或环境，详见[外部依赖](docs/外部依赖.md)。

## 工作流程

1. **明确任务。** 整理目标、系统边界、设计基准、指定方法、允许改动和验收条件。
2. **确定当前阶段。** 新流程可在任务允许时先建立完整的简化骨架；已有模型从当前有效阶段继续。
3. **执行专业工作。** 按需查询知识、推导参数、设置模型、处理报错或比较工况，保留实际输入与输出。
4. **复核系统影响。** 用当前工况检查设备，修改后重新核对上下游物流、循环、热量、压力和产品条件。
5. **整理交付。** 分别报告计算完成、软件运行、产品符合性和交付核验状态，列明尚缺的输入或证据。

单项查询、模板生成、公式核对或文档任务只执行相关步骤。完整建模过程见[全流程工作原理](docs/全流程工作原理.md)。

## 计算工具与知识调用

求解路由按问题区分读值、运行时联动、目标匹配、响应分析和多变量优化，帮助选择 Calculator、Design Spec/Vary、Sensitivity 或 Optimization 等适用方式。比较前明确哪些条件固定、哪些操作量需要联动。

设计阶段接口可调用本地知识检索和已有设备程序，返回查询、计算与输入缺口记录。知识条目按适用条件使用，项目数值取自当前资料或明确的计算推导。设备检查产生的修改建议，由相关流程模块实施并复算。

知识增补按资料逐份处理，先检查实际用途和已有覆盖：重复知识、无用内容跳过，只保留有用的增量。内容以完整知识块组织，读者能无歧义地复述其含义和必要条件即可，不追求零碎条目数量；查询先找足以回答问题的层次，需要时再下钻。具体见[知识入库与读取规则](plugins/chemical-engineering-skills/skills/chemical-engineering-expert/references/COMMON_SENSE_RAG.md)。

路由结果用于安排下一步工作；实际软件操作和验收另行执行。原生 Sensitivity 的目标接口资格核验仍待完成。接口、调用时机和范围见[内置工具使用说明](plugins/chemical-engineering-skills/skills/aspen-document-driven-flowsheet/references/aspen_builtin_solve_fit_tools.md)与[设计阶段调用](plugins/chemical-engineering-skills/skills/chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)。

## 0.4.6 更新：Agent 工作流与经验管理

0.4.6 汇集了任务组织、按需读取、决策树、文件影响与运行记录索引、经验收件和主动提醒的更新。现有 19 项 Skill 的输入、产物和协作关系已整理，配套工具可用于检查改动影响、文件身份和经验候选。收件校验与 GitHub 检查观察工具由独立的[公开经验收件库](https://github.com/milklong888/chemical-engineering-experience-inbox)提供。

经验维护区分临时收件和正式采用。正式整理沿用已有的资格与候选审核流程，保留规则版本、维护位置和回退记录；阶段提醒要求助手给出具体摘要、适用条件和投稿入口。

本次采用了哪些研究思路、实际改了什么，以及现在可以怎样使用，见[Agent 工作流统一更新说明](docs/Agent工作流更新_2026-09-12.md)。

### 经验提醒与投稿

从 0.4.6 起，19 个 Skill 的阶段收尾规则要求主助手检查是否形成了值得复用的新经验，并展示具体摘要、适用条件和投稿入口。已执行的方法核对实际版本与验证范围；思想原则先由使用者确认具体内容，再由助手审核。

使用者可以授权公开脱敏候选，按[中文投稿指南](https://github.com/milklong888/chemical-engineering-experience-inbox/blob/main/docs/USER_SUBMISSION_GUIDE.zh-CN.md)提交 PR。有效授权在其范围内沿用，拒绝或撤回后停止相应提醒和提交。临时收件与正式知识更新分别审核，详细流程见[经验提醒与收件规则](plugins/chemical-engineering-skills/skills/chemical-engineering-expert/references/EXPERIENCE_INBOX.md)。

提醒由助手执行，仍需检查具体操作是否完成。安装 Skill 不会自动采集或上传项目；其他电脑需要自行更新并重新安装。

## 安装条件与验证范围

完整离线包的依赖面向 **Windows AMD64、CPython 3.14**。按[使用手册](docs/使用手册.md)校验并安装，将项目资料与结果放在独立工作区。本地知识查询和常规设备计算可通过命令行执行，MCP 是可选接口；AI 对话是否联网取决于所用模型服务。

真实 Aspen Plus、EDR、SW6 操作需要目标电脑具备相应软件、许可和适配环境。当前项目的模型、设计条件、厂家资料和报价由使用者提供。

验证记录分别覆盖文件完整性、程序行为、工具调用和助手任务表现。软件检查通过不直接代表工程方案通过；具体项目仍需基于目标版本与实际交付文件验收。更新内容见[发行说明](https://github.com/milklong888/chemical-engineering-skills/releases/tag/v0.4.6)，验证方法见[验证说明](docs/验证说明.md)。

## 文档导航

- [使用手册](docs/使用手册.md)：安装、环境配置与操作示例。
- [模块说明](docs/模块说明.md)：19 个 Skill 的职责、输入和交接。
- [文件索引](docs/文件索引.md)：脚本、知识数据和模块文件。
- [后台运行与计算说明](docs/后台运行与计算说明.md)：参数计算与设备反馈。
- [Agent 工作流统一更新说明](docs/Agent工作流更新_2026-09-12.md)：任务组织、维护工具、经验复用与投稿。
- [决策树](plugins/chemical-engineering-skills/skills/chemical-engineering-expert/references/TASK_DECISION_TREES.md)：任务选择、排错和证据判断分支。
- [组织与影响索引](docs/skill_organization.md)、[观察索引](docs/observation_index.md)：维护时的引用检查和运行记录核对。
- [源码与数据边界](docs/源码与数据边界.md)、[来源与许可](docs/来源与许可.md)：组成、来源记录和使用条件。
