# 原两段脚本的保全式使用边界

原 22 个函数名保留。换算、流股卡格式、组分换行、块名提取、节点读取和 CSV 导出使用显式组件、分子量和输出路径。缺失 mol 字段、分子量或零分母会报错，不会补零。Calculator ID、初始化小流量和 SEP split 也必须由调用者显式提供。

`read_stream` 还要求每个数值字段的明确 `expected_units`，实际读回 UnitString 不一致或未知时保留原值到 `field_evidence`，正式单位字段置为未知，不能把 kPa 输出贴成 bar 后继续计算。它不默默转换单位；转换由已有单位工具在上游有依据地完成。

原 `segment_a_lines`、`segment_b_lines`、`audit_text`、`write_pfd` 的控制和输出结构由原 AST 机械转换；项目组分、MW、流量、工况、卡片、固定标号、系数与叙述常量已经外置到私有 profile。公开程序不自带历史项目 profile，也不以旧案例为默认。必须提供 profile 文件和其 SHA256，代码会检查文件身份与后续变更。

`synthetic_profile.json` 只用作数据形状与命令行测试，既不是实际化工输入也不是已验证 Aspen 模型，不能用来运行或交付。其 hash 可在 `SOURCE_PRESERVATION.json` 查到。新项目需要由当前来源与段边界合同构建自己的 profile；复制历史数值不构成授权。

```text
python build_two_section_corrected.py --profile <project-profile.json> --profile-sha256 <sha256> --section a --output-dir <new-empty-project-directory>
python build_two_section_corrected.py --profile <project-profile.json> --profile-sha256 <sha256> --section b --boundary-stream-json <same-case-stream.json> --output-dir <another-new-empty-directory>
```

输出只到指定空目录，已有文件拒绝覆盖。`run_case` 当前只生成输入候选与操作交接单，明确 `not_run`/`delivery_passed=false`；不调用 COM。导入后 SEP 赋值须由上游当前许可、真实节点单位和既有受监督 worker 完成；不能假称现有 no-edit 操作模板已经执行这些赋值。

交接单记录并哈希绑定既有 `aspen_operation_template.py`、`aspen_runtime.py`、`aspen_run_supervisor.py`。完成当前许可的输入变更后，由专业操作层做受监督 open/run/export，再使用现行精确文件 Summary/history 与产品/设备验收。普通运行返回值不是交付通过。

原不安全 `run_case` 实现完整保留在 `run_case.audit-only.txt`，带原文件身份、禁止默认检索/执行标识和具体替代入口；这不是丢弃原代码，也不是恢复旧的覆盖文件、无归属 COM、未知引擎状态视作成功的行为。本轮没有真实 Aspen 验收，也没有共享学习。
