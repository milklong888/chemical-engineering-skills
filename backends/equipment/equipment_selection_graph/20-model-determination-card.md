# 20 型号确定卡

每个位号必须有一张卡。没有卡的型号不得进入正式设备一览表。

## 卡片字段

| 字段 | 必填内容 |
| --- | --- |
| `equipment_tag` | 当前项目唯一位号 |
| `equipment_family` | 本图谱设备族ID |
| `process_function` | 由当前Aspen/流程文件证明的作用 |
| `same_equipment_sources` | 当前项目APW/BKP/DOCX/CSV/软件导出路径与哈希 |
| `operating_basis` | 介质、相态、流量、操作T/P、进出口、关键物性 |
| `design_basis` | 设计T/P、腐蚀、寿命、允许压降/性能、安全工况 |
| `standard_identity` | 标准号、版本、状态、官方URL、本地文件SHA256 |
| `standard_scope_match` | 适用/不适用/部分适用及理由 |
| `designation_grammar` | 型号各段含义；无统一语法则明确写 `not_standardized` |
| `lookup_chain` | 输入→舍入/上靠→标准页/表/行→输出 |
| `candidate_model` | 由标准或厂家产生的候选字符串 |
| `software_vendor_gate` | EDR/SW6/Column Internals/厂家曲线/数据表要求 |
| `verification_result` | 两侧复核、冲突、状态和日期 |
| `model_status` | 状态机枚举 |
| `forbidden_claims` | 本位号禁止写入的旧型号或越界结论 |

## 标准查表链格式

```text
项目输入
→ 单位统一
→ 结构型式判定
→ 标准适用范围检查
→ 参数上靠/圆整规则
→ 标准号-版本-页码-表号-行列
→ 候选型式/基本参数/型号段
→ 同设备热工/水力/机械或厂家性能复核
→ 型号状态
```

## 型号字符串拆解表

| 顺序 | 原字符串片段 | 字段含义 | 原始输入 | 查表/厂家来源 | 复核状态 |
| --- | --- | --- | --- | --- | --- |
| 1 |  |  |  |  |  |

若任何片段的含义或来源无法证明，整个字符串不得升级为 `same_equipment_verified`。

## 决策标签

- `correct_standard_model`：标准语法、查表链和同设备复核闭合。
- `correct_vendor_model`：厂家型号、工作点和正式数据表闭合。
- `standard_candidate`：标准系列闭合但软件/机械尚未闭合。
- `vendor_candidate`：厂家系列存在但工作点/材料尚未闭合。
- `custom_equipment_no_universal_model`：非标设备，输出型式和关键参数，不强造型号。
- `legacy_unverified`：仅从旧表、旧项目或无来源报告得到。
- `wrong_family_or_wrong_scope`：设备族或标准适用范围不符。
