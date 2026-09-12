# 工作区知识与工具入口

## 专业技能

安装后的技能根为`{CHEM_SKILLS}`。从
`chemical-engineering-expert/SKILL.md`确定设计与证据边界，再进入所需专业模块。
具体模块和文件见发行包`docs/模块说明.md`、`docs/文件索引.md`。

技能目录包含通用方法，不包含本项目的进料、设备尺寸、产品规格或运行结果。
项目变更和当前模型状态保存在本工作区。

## 随包后台与知识（优先读取）

后台根目录：`{CHEM_WORKSPACE}/chemical-engineering-runtime`。
统一查询与调用：`{CHEM_WORKSPACE}/chemical-engineering-runtime/tools/expert_cli.py`。
没有GUI依赖；不得因设备桌面程序未安装就放弃下面的已有接口。

| 旧逻辑资产或任务 | 该后台根目录下的实际位置 | 使用边界 |
| --- | --- | --- |
| `chemical_principles_knowledge/knowledge_graph` | `knowledge/chemical_principles/knowledge_graph/` | 原23张L3/L2/L1卡，原PDF/整页OCR不随包。 |
| `aspen_sun_lanyi_knowledge/knowledge_graph` | `knowledge/sun_lanyi/knowledge_graph/` | 原通用节点与方法；非项目默认值。 |
| `aspen_user_guide_v10_knowledge` | `knowledge/aspen_v10/` | 原操作细节；V10不替代目标版本字段证据。 |
| 原设备图谱/标准事实 | `backends/equipment/knowledge_graph/`与`backends/equipment/data/` | 保持原单位、适用分类、QA和消费者范围。 |
| 设备选型器 | `backends/equipment/app/equipment_design_agent.py` | 原JSON接口，先计算后选择；COM单独显式允许。 |
| 设备结果返回工艺模型 | `backends/process/feedback.py` | 有来源超限才生成修改候选；模型实施与同版复算仍须专业工作流。 |
| 求解工具选择 | `tools/aspen_tool_router.py` | `solve_route`按读值、运行关系、目标匹配和优化分类；返回待办，不运行Aspen。 |
| Skill文件组织与改动影响 | `tools/skill_organization.py` | 只读静态引用与反向影响候选；必须以`--root`指定完整源码/发行目录，不以runtime目录冒充19项Skill全库。 |
| 显式运行证据观察 | `tools/observation_index.py` | 只读取清单列明文件，分开哈希/身份/缺失状态；不生成工程验收、学习资格或权限。 |
| 本地MCP连接 | `tools/expert_mcp.py` | 九项无界面发现/查询/计算/反馈/路由工具；不自动启动Aspen。 |
| 原Aspen MCP封装 | `vendor/aspen-mcp-toolkit/run_offline_mcp.py` | 可选70工具；工程操作仍受输入、会话所有权和交付约束。 |

专业技能中保留的旧图谱名称先按此表解析，不在缺少原目录时重新造图谱或仅返回
“未安装”。不把未随包的原PDF页、私人案例或真实模型映射到方法卡冒充原件。

查询 `tools/expert_cli.py --query <问题>` 可联查方法节点与设备事实；限定
`--corpus chemical_principles|sun_lanyi|aspen_v10|equipment|equipment_standards` 可减少无关加载。
加 `--vector` 使用包内768维原算法哈希向量，未训练语义模型；默认基础查询不需
NumPy。`knowledge/manifest.json`与各后端清单说明实际载荷和缺口。

维护或对比运行记录时按需读取安装Skill中的
`chemical-engineering-expert/references/MAINTENANCE_TOOLS.md`；任务分流或排错分支不清楚时
读取其 `TASK_DECISION_TREES.md` 中相关部分。两者是现有规则的导航，不是第二套工程判定器。

各知识corpus的`knowledge_graph/00_ERROR_MEMORY.md`和`NEW_KNOWLEDGE.md`分别
作为错误优先检查与新知识待审入口。设备图谱的治理入口在`knowledge/equipment/`，
实际算法/数据库仍只有上表中的原后台一个owner。运行资产已冻结，不能边查询边
追加新事实。普通来源资料用 `knowledge/scripts/build_knowledge_version.py` 在
独立候选目录审核、重建与核验；任务经验须另在用户关闭当前任务后按中央进化
流程审查。两条路径都不自动覆盖活动库。

## 可选本地资料接入

以下完整原件或项目扩展可由使用者提供；不能和上面已随包的知识/算法混称缺失：

| 逻辑资产 | 作用 | 接入时记录 |
| --- | --- | --- |
| 化工原理图谱 | 守恒、平衡、传递、分离及单元操作的方法和来源。 | 资料版本、层级索引、原页位置、公式核验状态。 |
| Aspen操作知识 | 相应版本的卡片、字段、模型和运行方法。 | 软件版本、合法帮助位置、实际字段核对。 |
| 设备与标准图谱 | 设备身份、公式族、参数来源和适用标准。 | 标准版本、公式单位、设备和工况适用范围。 |
| 项目专用图谱 | 当前项目的原始要求、已采用方案和同案证据。 | 项目身份、访问范围、当前权威、允许的查询范围。 |
| 项目设备补充资料 | 同设备厂家曲线、报价、材料及软件结果。 | 设备身份、适用工况、版本、来源和验收状态。 |

将实际路径写入本地`assets.local.json`或项目自己的资产表，原始资料就地保留。
不要将该本地配置或数据提交到公开仓库。读取资源前核对其来源和用途；宏观问题
优先读取原则层，需要数值时再查看方法及原始证据。

## 检索

`scripts/vectorize_workspace_knowledge.py`和`query_workspace_vectors.py`提供
本地轻量索引构建和查询，`retrieval_routes.json`定义专业路由。构建前核对输入
目录，只索引适用的技能与已授权资料。源电脑私有全局索引不分发；随包
`knowledge/vectors/`是从经审查公开原节点实际生成的独立索引，不是空配置。

未出现在随包清单的项目专用资料是显式项目输入。用本地资产表明确其位置、权限
与范围；没有原始资料时不得将引用描述为已核验。
