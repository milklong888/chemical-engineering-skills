# 原设备源码维护区，不是第二运行引擎

这里保留原设备 2.3 系列中的通用算法、数据重建、解析、审计与回归代码。原有函数和类完整保留；机器绝对路径和少数私人文件名用显式占位符参数化，变换与两端 SHA256 在上级 `script_source_manifest.json` 和 `manifest.json` 中逐项登记。私人项目报表数值及 GUI/远程审计入口另行保留在原工作区，不混入本目录。

- 当前运行职责归发行的 `backends/equipment` 2.4.0；同名维护脚本不表示与 2.4 同一版本或同一哈希。
- 本目录不注册到 MCP、Skill 自动发现或默认 RAG，不与当前后端并行选择算法。
- 源码保留不等于可运行。重建通常需要用户自备标准、源图、项目输入、旧资产布局及列明的 Python/Node 依赖；先复制到明确维护沙盒，核输入与输出后才可运行。
- 旧默认参数、原数据晋升流程、脚本输出的旧 PASS 和示例不是当前工程或共享学习的验收依据。原标准重建脚本不获准改当前知识或当前严格标准。
- 常规条目仅做静态检查和源码保全，不执行旧 COM、GUI、远程模型或数据晋升。显式参数化的三个维护入口另有受限回归：原建图函数对原解析表格等值检查、合成 DOCX 提取和设备分段 CLI；这些测试不构成当前工程通过证据。

三个项目映射入口的输入与输出边界见 [显式维护配置合同](equipment_2_3/scripts/MAINTENANCE_PROFILE_CONTRACT.md) 和 [源码身份](equipment_2_3/scripts/SOURCE_PRESERVATION.json)。原 `equipment_calc.py` 私案副本不在此处重复公开；原件完整保留，参数化算法的唯一运行职责在 [当前设备后台](../../backends/equipment/README.md#valuable-legacy-audit-scripts-remain)，两端身份已登记。

`source_build_only: true`、`automatic_activation: false`、`default_retrieval_eligible: false`。
