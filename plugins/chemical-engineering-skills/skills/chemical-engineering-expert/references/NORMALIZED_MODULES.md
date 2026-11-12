# 规范化模块与离线工具

本页负责发现入口和状态，不重复专业计算规则。完整机读目录在发行根的
`runtime/module_catalog.json`：12个维护单元、23份来源提案各自记录owner、
处置、实现状态和限制。提案合并、代码安装与工程经验准入分别记录。

| 当前问题 | 唯一专业实现或正文 | 使用边界 |
|---|---|---|
| CSV时间网格、文件清单、历史解析、外部调用计划 | operations的`scripts/dynamics_tools/` | 五项离线工具；计划只输出参数，不启动外部程序 |
| 四项EDR/填料水力学输入诊断 | EDR的[工具合同](../../aspen-edr-rating-delivery/references/engineering_checks_tools.md) | 读取调用者资料；不替代原生计算、操作图位置或制造验收 |
| PFS/Export18布局、边界对比、文件链接辅助 | operations的[辅助工具](../../aspen-plus-operations/references/offline_module_tools.md) | 原生回读及HTTP服务生命周期分别核实 |
| 精度/冷启动观测与隔离变体 | error-repair的[收敛案例](../../aspen-flowsheet-error-repair/references/cases/convergence_diagnostics.md)及`scripts/convergence_diagnostics/` | 只审计显式观测；原有求解容差锁继续适用 |
| 双效跨塔连接与净边界 | [双效专业入口](../../aspen-double-effect-distillation/SKILL.md) | 来源审查过的方法与示意图，不携带项目值或原生运行成绩 |
| 临时经验收件 | [原有收件导航](EXPERIENCE_INBOX.md) | 协议和准入工具仍由经验库维护 |

通过现有专家CLI使用：

```json
{"operation":"module_catalog","payload":{}}
```

```json
{"operation":"module_check","payload":{"tool":"edr.screen_pipe_candidates","inputs":{"catalog":[]}}}
```

第二例只说明调用形状；完整有效输入采用EDR owner的合成示例，不能把空目录当作
已验证的设备目录。使用`--schema module-tools`发现九项允许调用的操作，或从已有
专家MCP调用`module_catalog`、`module_check`。CLI与MCP最终调用同一专业实现。

## 状态和编号

- 规则键使用`proposal_id#local_rule_id`。两个来源均使用P0-018时，不能用裸编号合并。
- 代理模型和推理强度由当前任务授权、可用模型及分工规范决定；旧固定型号不是默认设置。
- 材料库架构、方法预算倍率、操作图位置诊断、自动告警诊断及完整原生依赖解析仍按
  目录中的拟定状态处理。FC检查不计算操作点位置。
- 两组原归档代码继续保留其资格限制，只返回来源定位；默认目录和允许执行表均排除它们。
  `include_archives=true`只显示元数据，不复制、安装或执行归档代码。
- `completed`表示调用完成；Dynamics先读`result.status`，有效后才读`matches`；EDR读`result.diagnostic_status`。错误分支可以没有`matches`。
  它们均不授予原生软件、精确文件或工程通过。

来源身份见`runtime/module_sources.json`和各子模块的迁移记录；本次维护不重新收件
旧提案，也不从任何放宽案例导入模型、数值、图、修复轨迹或成功标签。
