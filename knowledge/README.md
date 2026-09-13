# 随包原知识与离线查询

日常查询见下文；增补资料或从已关闭任务提炼候选时，使用
[独立知识版本维护入口](MAINTENANCE.md)。来源增补与任务经验进化分开准入，
构建工具只产出独立候选目录，不自动改活动库；主审采纳后的资料随完整产品维护和发布。安装后错误/学习责任通过
[逻辑owner路由](OWNER_ROUTES.md)定位，不依赖另外两个仓库或旧电脑路径。

这里保留原图谱中的通用内容，不用新的短摘要替换原方法。化工原理的 23 张思想、原理与方法卡，孙兰义图谱的 390 条原节点和通用方法章节，以及 V10 的 6415 个细节标识与 39 章导航按原 ID 可查。

另已采纳 14 个反应器与反应过程知识块及 13 个精馏动态控制与特殊分离知识块；当前共 6900 条记录，其中 6877 条可进入默认检索。新增主题、实际处理范围与来源编号见[新增知识说明](intake/README.md)，最新数量以 `manifest.json` 和 `vectors/config.json` 为准。

V10 中 6392 条细节正文可用；23 条较长、含公式/OCR/示例表达的记录逐项待核，保留原 ID、位置与正文哈希，不返回未核正文。571 个整页兜底正文和化工原理的 687 页 OCR 库不在公开包。它们未被删除，原工作区仍保留；本发行也不会暗中访问原电脑。

```text
python knowledge/scripts/verify_knowledge.py
python knowledge/scripts/query_knowledge.py --query "高温公用工程 预热 压缩" --json
python knowledge/scripts/query_knowledge.py --query Wegstein --corpus aspen_v10 --detail --json
python knowledge/scripts/query_knowledge.py --node-id UG10-CH17-D091 --full-text --json
python knowledge/scripts/query_knowledge.py --query "预热 压缩" --vector --json
```

默认查询只使用包内文件与 Python 标准库，复用原 V10 字面检索评分。默认按思想 L3→原理 L2→方法 L1→细节 L0 排序；明确公式/计算或 `--detail` 时从方法下钻。它不等于云端语义模型，不下载模型、不联网、不启动 Aspen、不修改索引和案例。

可选 `--vector` 使用随包 NumPy 数值矩阵，768 维、float32，实际行数见 `vectors/config.json`。它直接复用原工作区的哈希 n-gram 向量、准入过滤和检索路由函数，不是新训练的 embedding。23 项待核正文不进入矩阵。维护者可用 `python knowledge/scripts/vector_adapter.py build` 从同一原记录重建；运行查询只读，并核对输入与既有检索代码哈希，变化后要求重建，不静默使用过期向量。

结果的 `knowledge_layer` 是抽象层；`provenance_path` 是来源位置，二者不混淆。所有原手册数值、旧版本默认值和教学例题均不得直接成为当前项目值。原文中的历史工作区文件名、未随包源页、旧流程说明是来源导航，不代表这些文件在包内，也不覆盖当前专业 Skill 的严格验收。

`manifest.json` 核对实际文件 SHA256 和选取的原始字节段；`records.jsonl` 是同一内容的查询投影；`script_source_manifest.json` 逐个列出 114 个原脚本来源、依赖与公开/维护状态。源码保留与运行闭包分别标注：需要教材原件、OCR/外部软件、旧设备资产或项目表格的重建工具不能冒称开箱即用。设备当前执行入口仍由发行的 `backends/equipment` 管理；维护源码不自动激活第二个设备引擎。

孙兰义经典案例按节保留通用方法、隔离私人项目节，不因同文件含项目内容而整份丢弃。来源定位不代表教材/商业帮助原文的再分发许可；原 PDF、整页文字和私人项目历史不随包。新增通用知识释义与既有内容分别保留来源和采纳记录；普通资料维护不冒充任务经验晋升或工程验证。
