# 原始维护脚本的显式项目输入

这些脚本保留原来的表格提取、来源分类和建图控制结构，属于源码维护入口。
日常设备计算仍由 `backends/equipment` 承担；维护结果不自动进入默认检索、
共享学习或正式工程验收。输入文档、标准原件和私人案例配置不随公共包发布。

## 从 DOCX 提取表格和证据段落

`extract_docx_tables.py --source-root <DOCX目录> --output-root <空输出目录>`
保留每张表的行列、CSV、标题线索和证据段落索引。缺省文档 ID 为文件内容
SHA256 的确定性前缀，不从文件名推断项目身份。可选 `--id-mapping <JSON>`
接受“文件名或完整文件 SHA256 → 文档 ID”的显式字典；ID 只允许字母、数字、
下划线和连字符。重复 ID、来源与输出重叠、已有输出均在写入前拒绝。
需要 `python-docx`，不会启动 Word、Aspen 或外部模型。

## 按已解析表格重建案例选型图

`build_selection_learning_graph.py --profile <JSON> --profile-sha256 <SHA256>
--source-root <含data/tables的目录> --standards-root <已审标准目录>
--output-root <独立空目录>`。

配置 schema 为 `selection-maintenance-case-profile-v1`，包含 `literals`、
`joined_strings` 两个函数级字面量映射；必须明确
`learning_eligible=false`、`default_retrieval_eligible=false`。
来源 ID、报告叙述、案例阈值和案例型号只能由用户当前配置提供，无公开项目默认。
配置固定 SHA256 后才允许生成 CSV、节点/关系 JSON 和 Markdown；
配置可修改输出中的文本，但不能执行 Python，也不能经表格路径越出来源目录。

原来直接解 ZIP 的函数保留在源码供审计，但本 CLI 遇到 ZIP 即拒绝。
请提供另外审查过的已解包标准文件。本入口不替代标准许可、版本核对、
厂家资料或同设备软件校核。原历史 profile 仅保存在本任务私有保全目录，
没有配套 profile 时明确报输入缺口，不生成“空成功图谱”。

## 源码身份

原始文件 SHA、公开参数化文件 SHA、保留函数和限定用途见本目录
`SOURCE_PRESERVATION.json`；全部原图谱脚本的去向见
`../../../script_source_manifest.json`。原件未改，公开副本不携带私人报告叙述。
