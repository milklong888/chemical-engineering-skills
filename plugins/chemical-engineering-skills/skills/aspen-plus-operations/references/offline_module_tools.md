# 操作层离线辅助工具

这些脚本附属于本专业，输入规则和限制保存在各目录的README、方法说明及来源记录。
它们可独立运行，不要求启动Aspen；原生操作仍使用原有受控会话与验收链。

| 目录（相对本Skill） | 入口与用途 |
|---|---|
| `scripts/dynamics_tools/` | `toolpack.py`的CLI、`mcp_server.py`的stdio入口；五个离线工具，包括显式网格/文件检查及不会执行的外部调用计划 |
| `scripts/native_layout/` | `pfs_layout.py`；读取、转换已支持的Export18/PFS布局文本，原生导入结果另行回读 |
| `scripts/flowsheet_boundary/` | `boundary_compare.py`等；对显式边界资料作比较；COM回调需要另有获准会话 |
| `scripts/artifact_delivery/` | `artifact_bridge.py`；文件已存在但客户端链接失败时按明确生命周期使用，结束后关闭自有服务 |

Dynamics历史工具复用本Skill现有`scripts/aspen_evidence.py`，先核固定来源身份，
不维护第二个活动解析器。更换来源或版本须更新迁移记录及相关测试，不能只跳过哈希。
本包不包含原生Dynamics控制后台；目录中的Plus、专家和原生审计外部入口仍分别核查。

统一发现和九项EDR/Dynamics调用见
[模块目录](../../chemical-engineering-expert/references/NORMALIZED_MODULES.md)。
外部服务路径存在、脚本退出0或HTTP可下载，不证明软件导入、完整依赖或工程验收。
