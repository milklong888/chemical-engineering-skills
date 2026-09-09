# 发布模块与本地资产登记

本表描述本发行包的模块归属，不包含源电脑或私人项目路径。安装后的技能根为
`{CHEM_SKILLS}`，各模块的唯一入口为对应目录的SKILL.md。

| 模块 | 职责 | 主入口 |
| --- | --- | --- |
| aspen-adaptive-generalization-loop | 同基准适应性试算与规律检查 | [SKILL.md](../../aspen-adaptive-generalization-loop/SKILL.md) |
| aspen-document-driven-flowsheet | 文档驱动流程建模与阶段组织 | [SKILL.md](../../aspen-document-driven-flowsheet/SKILL.md) |
| aspen-edr-rating-delivery | 换热器EDR计算流程和交付检查 | [SKILL.md](../../aspen-edr-rating-delivery/SKILL.md) |
| aspen-flowsheet-cost-skill-builder | 设备费用来源与项目分析方法 | [SKILL.md](../../aspen-flowsheet-cost-skill-builder/SKILL.md) |
| aspen-flowsheet-error-repair | 同案故障诊断与修复 | [SKILL.md](../../aspen-flowsheet-error-repair/SKILL.md) |
| aspen-heat-pump-distillation-replacement | 精馏热泵替换与边界比较 | [SKILL.md](../../aspen-heat-pump-distillation-replacement/SKILL.md) |
| aspen-kinetics-documentation | 动力学来源、换算和模型输入说明 | [SKILL.md](../../aspen-kinetics-documentation/SKILL.md) |
| aspen-non-reactor-equipment-cost | 非反应器设备费用结果提取接口 | [SKILL.md](../../aspen-non-reactor-equipment-cost/SKILL.md) |
| aspen-plus-operations | Aspen卡片、运行、导出与证据读取 | [SKILL.md](../../aspen-plus-operations/SKILL.md) |
| aspen-plus-template | 组分模板创建和文件验证 | [SKILL.md](../../aspen-plus-template/SKILL.md) |
| aspen-pressure-pfd-delivery | 全流程压力路径与图纸交付 | [SKILL.md](../../aspen-pressure-pfd-delivery/SKILL.md) |
| aspen-tower-optimization-workflow | 塔方案和操作条件优化 | [SKILL.md](../../aspen-tower-optimization-workflow/SKILL.md) |
| aspen-two-section-flowsheet | 分段合同及跨段接口 | [SKILL.md](../../aspen-two-section-flowsheet/SKILL.md) |
| chemical-engineering-expert | 设计基准、宏观方案、证据和方法审查 | [SKILL.md](../../chemical-engineering-expert/SKILL.md) |
| chemical-equipment-selection-audit | 设备选型计算和来源审查 | [SKILL.md](../../chemical-equipment-selection-audit/SKILL.md) |
| chemical-tower-design | 塔工艺设计、负荷和设备资料 | [SKILL.md](../../chemical-tower-design/SKILL.md) |
| equipment-design-app | 随包无界面设备后台的调用合同 | [SKILL.md](../../equipment-design-app/SKILL.md) |
| subagent-dispatch | 独立事实任务分工与结果归并 | [SKILL.md](../../subagent-dispatch/SKILL.md) |
| sw6-scripted-equipment-design | SW6输入和结果的接口审查 | [SKILL.md](../../sw6-scripted-equipment-design/SKILL.md) |

每个模块的references/ERROR_MEMORY.md保存检查规则，NEW_KNOWLEDGE.md保存
新增方法的状态。备份与发行副本不建立第二套活动权威。

## 随包图谱及其治理入口

后台根目录为`{CHEM_WORKSPACE}/chemical-engineering-runtime`，以下位置相对此根。
先读各图谱的错误记忆，再按最高充分层检索；新知识先登记候选与来源，不能直接
追加到已签名的运行数据库或向量矩阵。

| 图谱 | 原节点与查询资料 | 错误/新知识入口 |
| --- | --- | --- |
| 化工原理 | `knowledge/chemical_principles/knowledge_graph/` | 同目录`00_ERROR_MEMORY.md`、`NEW_KNOWLEDGE.md` |
| 孙兰义方法图谱 | `knowledge/sun_lanyi/knowledge_graph/` | 同目录`00_ERROR_MEMORY.md`、`NEW_KNOWLEDGE.md` |
| Aspen V10操作细节 | `knowledge/aspen_v10/knowledge_graph/` | 同目录`00_ERROR_MEMORY.md`、`NEW_KNOWLEDGE.md` |
| 设备规则及标准事实 | `backends/equipment/knowledge_graph/`、`backends/equipment/data/` | `knowledge/equipment/00_ERROR_MEMORY.md`路由到已有专业owner，`knowledge/equipment/NEW_KNOWLEDGE.md`记录待审入口 |

统一查询为`tools/expert_cli.py`。原始教材/商业帮助整页、私人项目图谱与真实
工程结果仍是可选本地资产；位置、来源、版本和项目范围按工作区
LOCAL_KNOWLEDGE_GRAPH_LINKS.md登记。缺少的是具体原件或证据时，不能把包内
已经提供的结构化知识和算法也说成未安装，更不能以其他项目数值补齐。
