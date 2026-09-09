# 设备程序到流程设计的可选本地反馈接口

工程判断合同由 `chemical-engineering-expert/references/PROCESS_EQUIPMENT_FEEDBACK.md`
维护。本文件提供外部接口约定，不包含选型程序、商业数据库或私有 RAG 正文。

用户可在配置的 `{CHEM_WORKSPACE}` 安装并核验既有设备桥，再按实际路径调用：

```text
python -B -X utf8 "{CHEM_WORKSPACE}/integrations/github_20260909/selector_bridge.py" --request <equipment-design-agent-request-v1.json> --output <new-feedback.json>
```

该示例只在用户提供并验证此桥时可用；路径不存在时明确报告未安装，不能说
当前 Skill 已具有本地程序或数据库。外部设备 Agent 的历史接口核查提交为
`e3a5f1bffd1889b8c70ae0b1f3343f7fccbeea20`；升级须重新核验接口、规则、
源码和 ACTIVE 数据清单，不用旧回执替代新版本测试。

已知接口族为 `manual_match/manual_batch/auto_match/aspen_derive`。响应应保留
原始文件/哈希、各设备参数和公式链、规则、能力冲突或数据/目录缺口、调整候选。
实际支持项以当前外部程序能力声明和同版本验证为准，不由此说明补造。

反馈到流程层的候选至少包含父模块/子设备映射、触发证据、数量与连接方式、
单台工况、相态/温差/压力/控制检查、受影响物流、执行及重算状态。
`TYPE_SCREENING` 或一个型号不代表流程合理或正式验收。

数据由用户合法提供，校验当前注册资产的 exact hash；本包不下载、恢复或
重新分发缺失的商业库/教材/私有正文。真实 BKP 导入仍须用户授权并经现有
Aspen 机械接口处理；只读反馈桥本身不承担 COM 运行或改模型。

