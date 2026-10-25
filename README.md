# 化工设计专家工作库

作者：milklong（GitHub：milklong888） · [版权、来源与AI辅助编辑声明](ATTRIBUTION.md)

从任务书、文献条件或已有 Aspen 模型出发，完成流程规划、简化骨架、单模块细化、设备计算反馈和全流程复核。这套工作库把 **19 个 Skill、分层知识检索、17 类设备计算后台及可复用脚本**接在同一条工作线上，适合完整流程生成，也支持单塔优化、模型排错、设备审查、费用整理和技术说明等独立任务。

使用者说明设计目标并提供当前资料，助手负责选择所需模块。每一步留下所用依据、修改内容、计算结果和待解决问题，后续工作据此继续。

当前维护版为 **0.4.12**。自研代码、脚本、Skill 指令和说明文字按 [MIT](LICENSE) 开源；第三方组件、专著与标准资料按[各自许可和使用范围](THIRD_PARTY_NOTICES.md)处理，不把整个资料库笼统称为 MIT 开放数据。公开和允许修改副本，不授予他人原仓库写入权限。

[下载完整发行包](https://github.com/milklong888/chemical-engineering-skills/releases/latest) · [安装与使用](docs/使用手册.md) · [按图理解工作流](docs/工作流与功能说明_0.4.10.md) · [19 个模块的详细说明](docs/模块说明.md) · [脚本与文件索引](docs/文件索引.md)

[![从设计资料到可核验的 Aspen 全流程](https://github.com/milklong888/chemical-engineering-skills/releases/download/v0.4.10/aspen-workflow-overview.png)](https://github.com/milklong888/chemical-engineering-skills/releases/download/v0.4.10/aspen-workflow-overview.png)

*点击图片查看原尺寸。左侧按工作顺序展开，右侧分别说明外置专著和设备后台的调用；底部是任务结束后的经验更新。*

## 能完成什么

完整流程任务以自然语言要求和来源资料为起点，先补齐模块、物流、反应与分离目标、物性方法和热压配套，再建立能够实际运行的简化模型。有循环时从运行结果取得初值，然后逐个细化反应、分离和能量模块，将设备计算发现的实际限制带回模型修改，最后接回整条流程并验收。

已有模型可以从当前有效阶段继续。只需要优化一座塔、核查一台换热器、定位循环故障、生成组分模板或整理动力学依据时，直接进入相应专业模块。交付按任务范围组织，可包括模型文件、同次运行导出、设备计算表、来源与变更记录，以及 PFD 或技术说明。

## 沿着图看工作流

### 1. 专家规划：把设计要求变成明确的模块链

助手先确定进料、产品、反应条件与程度、分离目标和指定方法，再沿组分去向安排模块及其连接。每个模块都需要物性依据；接口处同时检查温度、压力、相态、压降、预热、升压和冷却需求。循环、补料、吹扫及废物流也在这一阶段交代清楚。能够从资料、单位换算或衡算得到的量先推导，尚不确定的条件保留依据和待核项。

内置图谱帮助联系基本原理与 Aspen 操作；物性方法适用性存疑时，优先查询当前工作区登记的外置专著。完整流程的同一版模块链随后接受五份独立审查，主助手处理歧义与漏项，形成后续建模共同遵循的设计基准。

### 2. 简化全流程：先得到全局物料与循环关系

在允许简化的范围内，反应用 RStoic、分离用 SEP 搭建骨架，换热器、加热冷却器、泵、压缩机及实际循环仍按其物理作用保留。骨架在 Aspen 中运行后，从同次导出读取循环流量、组成、温压和相态初值；无循环的流程记录其依据。随后由三份独立复核对照实际连接、参数、关键元件与热力学依据。

### 3. 模块细化与回装：计算结果要经得起设备检查

从骨架中取出一个功能模块，固定入口和目标，按对应专业方法建立严格模型。这里的“岛”是单独计算、验证的模块，细化后仍替换回原接口。普通精馏先复制进料到子模板，用 DSTWU 取得初估，再建立带塔内 Design Spec/Vary 的 RadFrac；在同一纯度和回收率要求下比较进料板，再调整总板数。

原生工具按问题选用：读取已有数值、建立随运行更新的关系、反求目标操作量、检查响应区间和约束优化，分别对应结果读取、Calculator、Design Spec/Vary、Sensitivity 和 Optimization。它们可以按需要组合，具体建卡和运行由软件操作层执行。

模块细化完成后，用最新同版工况逐台检查实体设备。真实单机限制可能要求换热分段、压缩分级、并联或改型；选定变化回到模块实施并复算。各模块逐个接回后，整厂重新计算循环、产品、热量和压力，并复查所有实际出现且适用的设备。

### 4. 软件执行与交付：核对最后交付的那份文件

现有脚本和 COM 负责建卡、运行、保存及导出，可选 MCP 只执行当前提供方已发现并核实的机械操作，Aspen 原生模块和求解器负责模拟。随包 MCP 并不等于已具备所有原生 Calculator、Design Spec 或 Optimization 的自动建卡接口；这些对象仍须按目标版本的方法建立、导出并核验。正式交付时，精确交付路径的文件需在没有模型编辑的情况下复开运行：经核实的 Summary 全部实际列、同次 Control Panel 消息和原始 `.his` 都满足零错误、零警告要求。默认及已有求解容差保持不变，产品、衡算、设备与目标版本兼容性另行核验。

### 5. 任务结束后的自进化：把有效经验放回合适的位置

用户明确结束当前任务后，才整理任务经验。一条线提炼宏观设计原则与行事方法，另一条线检验初值、控制顺序和操作关系是否带来可复现的收敛或优化改善。候选经过来源核验、对照或反例检查，再更新负责该主题的 Skill 或图谱，并保留版本和回退记录。局部放宽验收的案例及其派生结果只留项目记录，不进入共享经验。

完整步骤、每阶段产物和调用依据见[工作流与功能说明](docs/工作流与功能说明_0.4.10.md)；实际建模入口见[建模从哪里开始](docs/modeling_start_here.md)。

## 知识与设备怎样参与设计

**内置图谱**随包提供，围绕化工原理、方法适用性和 Aspen 操作组织内容。查询先找到能回答当前问题的层次，需要计算或操作时再下钻到公式、字段和来源。**外置专著图谱**由工作区另行登记，保存专著与手册的章节、主题、知识单元及原页依据；它在需要时补充判断，与内置图谱分别管理。两者都保留来源和适用范围，项目参数来自当前资料或明确推导。[知识结构与检索](knowledge/README.md) · [来源与许可](docs/来源与许可.md)

**设备后台**接收同版工况与设备用途，先统一单位并计算可闭合参数，再进行初步型式和能力校核。换热器尺度受限时研究分段并重算温态和累计压降；泵、压缩机按扬程或压比限制与流量限制分别研究串联和并联；塔按水力容量或分离分段需求判断。程序支持 17 类设备，按实际设备清单调用，并单列资料、目录和未知家族缺口。初选、设备评级和厂家定型属于不同工作阶段。[设备计算与反馈过程](docs/后台运行与计算说明.md)

这些能力通过资料整理、方法编排、脚本封装和回归检查形成。知识维护保留原始来源、抽象层次、适用条件和计算链，任务经验按上述流程逐步积累；本项目不包含重新训练的基础模型权重。

## 19 个 Skill：按任务进入

下表中的模块名称直接链接到 `SKILL.md`；“详细说明”介绍其输入、工作过程、产物和相关文件。日常使用无需记住所有名称，助手按任务和阶段选择。

| 模块入口 | 适合交给它的任务 | 工作过程与文件 |
| --- | --- | --- |
| [化工专家](plugins/chemical-engineering-skills/skills/chemical-engineering-expert/SKILL.md) | 宏观合理性、方法与设计基准、跨模块统筹 | [详细说明](docs/模块说明.md#module-01) |
| [文档驱动全流程](plugins/chemical-engineering-skills/skills/aspen-document-driven-flowsheet/SKILL.md) | 由资料构建骨架、逐模块细化并回装 | [详细说明](docs/模块说明.md#module-02) |
| [分段与接口](plugins/chemical-engineering-skills/skills/aspen-two-section-flowsheet/SKILL.md) | 工段边界、气液交接、溶剂返回和跨段物流 | [详细说明](docs/模块说明.md#module-03) |
| [Aspen 公共操作](plugins/chemical-engineering-skills/skills/aspen-plus-operations/SKILL.md) | 文件读写、建卡、运行、导出和精确文件检查 | [详细说明](docs/模块说明.md#module-04) |
| [组分模板](plugins/chemical-engineering-skills/skills/aspen-plus-template/SKILL.md) | 按组分清单、CAS 和目标版本生成并复核模板 | [详细说明](docs/模块说明.md#module-05) |
| [流程故障处理](plugins/chemical-engineering-skills/skills/aspen-flowsheet-error-repair/SKILL.md) | 输入、物性、循环、控制及产品异常的诊断修复 | [详细说明](docs/模块说明.md#module-06) |
| [塔建模与优化](plugins/chemical-engineering-skills/skills/aspen-tower-optimization-workflow/SKILL.md) | DSTWU 到严格塔、塔内设计规定、进料板与级数比较 | [详细说明](docs/模块说明.md#module-07) |
| [热泵精馏](plugins/chemical-engineering-skills/skills/aspen-heat-pump-distillation-replacement/SKILL.md) | VRC/MVR 塔岛改造，或审查节能与电耗主张 | [详细说明](docs/模块说明.md#module-08) |
| [压力路径与 PFD](plugins/chemical-engineering-skills/skills/aspen-pressure-pfd-delivery/SKILL.md) | 压力预算、升降压设备及流程图与报告一致性 | [详细说明](docs/模块说明.md#module-09) |
| [设备计算后台](plugins/chemical-engineering-skills/skills/equipment-design-app/SKILL.md) | 参数推导、17 类设备初选、标准查询与流程反馈 | [详细说明](docs/模块说明.md#module-10) |
| [设备选型审查](plugins/chemical-engineering-skills/skills/chemical-equipment-selection-audit/SKILL.md) | 审查设备报告、公式、单位、参数来源和差异根因 | [详细说明](docs/模块说明.md#module-11) |
| [塔设备设计](plugins/chemical-engineering-skills/skills/chemical-tower-design/SKILL.md) | 塔径、内件、水力学、压降、负荷图及机械交接 | [详细说明](docs/模块说明.md#module-12) |
| [EDR 评级与集成](plugins/chemical-engineering-skills/skills/aspen-edr-rating-delivery/SKILL.md) | HeatX 覆盖、真实 EDR 运行、文件绑定与评级检查 | [详细说明](docs/模块说明.md#module-13) |
| [SW6 字段传递审查](plugins/chemical-engineering-skills/skills/sw6-scripted-equipment-design/SKILL.md) | 经验证的字段映射、同设备读回及计算书核对 | [详细说明](docs/模块说明.md#module-14) |
| [非反应器设备费用](plugins/chemical-engineering-skills/skills/aspen-non-reactor-equipment-cost/SKILL.md) | 同案 AEPA 明细提取、设备覆盖及购置费汇总 | [详细说明](docs/模块说明.md#module-15) |
| [新流程费用方法](plugins/chemical-engineering-skills/skills/aspen-flowsheet-cost-skill-builder/SKILL.md) | 物理采购项映射、成套边界、费用来源与批量方法草案 | [详细说明](docs/模块说明.md#module-16) |
| [动力学技术说明](plugins/chemical-engineering-skills/skills/aspen-kinetics-documentation/SKILL.md) | 文献速率式、单位换算、Aspen/USER 参数与导出对应 | [详细说明](docs/模块说明.md#module-17) |
| [多工况自适应模板](plugins/chemical-engineering-skills/skills/aspen-adaptive-generalization-loop/SKILL.md) | 代表样本调试、控制关系形成及多进料复验 | [详细说明](docs/模块说明.md#module-18) |
| [子代理协作](plugins/chemical-engineering-skills/skills/subagent-dispatch/SKILL.md) | 独立读取、检索、执行和复核的分工与主代理整合 | [详细说明](docs/模块说明.md#module-19) |

## 安装、验证和继续阅读

完整离线发行包提供知识正文与索引、设备后台、脚本和固定依赖，运行不依赖另外两个来源仓库。完整依赖包面向 Windows AMD64、CPython 3.14；解释器、合法 Aspen／EDR／SW6 安装、项目资料和必要的厂家或费用数据由使用环境提供。知识查询与常规设备计算可用本地命令行执行，MCP 为可选调用方式；模型对话是否需要联网取决于所用服务。

具体模块的可执行部分、接入模板和外部依赖分别说明。SW6 模块提供映射与读回的工作方法，费用模块需要实际经济包或经审核的价格来源。程序回归、文件完整性与工程模型验收各有对应记录，见[验证说明](docs/验证说明.md)和[0.4.11 维护记录](docs/维护记录_0.4.11.md)。0.4.11 整理许可、说明与历史入口，不宣称新增工程仿真能力。

| 想继续了解 | 入口 |
| --- | --- |
| 安装、环境与使用示例 | [使用手册](docs/使用手册.md) |
| 按流程图逐步理解系统 | [工作流与功能说明](docs/工作流与功能说明_0.4.10.md) |
| 找某个模块的方法和脚本 | [模块说明](docs/模块说明.md) · [文件索引](docs/文件索引.md) · [原脚本目录](plugins/chemical-engineering-skills/skills/aspen-document-driven-flowsheet/references/script_template_catalog.md) |
| 构造设备、压力、知识查询请求 | [后台运行与计算说明](docs/后台运行与计算说明.md) · [外部依赖](docs/外部依赖.md) |
| 知识来源、维护与经验整理 | [知识库](knowledge/README.md) · [知识维护](knowledge/MAINTENANCE.md) · [经验更新流程](plugins/chemical-engineering-skills/skills/chemical-engineering-expert/references/EVOLUTION_LOOP.md) |
| 版本变化与发行文件 | [发行记录](https://github.com/milklong888/chemical-engineering-skills/releases) · [当前维护记录](docs/维护记录_0.4.11.md) · [历史文档归档](docs/archive/README.md) |
| 开源与资料边界 | [MIT](LICENSE) · [第三方与数据范围](THIRD_PARTY_NOTICES.md) · [依赖许可清单](docs/第三方依赖许可清单.md) |
