# 显式证据观察索引

`tools/observation_index.py` 只读取指定清单和该清单列出的证据文件，输出 JSON 审计索引。它不扫描目录、不导入工程运行时、不执行模型，也不写入原记录或产生评分。

文件哈希相符只说明读取字节符合清单预期；身份字段相符只说明指定字段按原类型相等。工具不判断工程验收、来源真伪、学习资格、用途授权或候选晋级。原始资格回执可以作为一个文件关联，其 `status` 仍是未经本工具解释的原记录。

## 调用

```text
python -B -X utf8 tools/observation_index.py --manifest E:/observation/manifest.json --evidence-root E:/observation/evidence
```

两个入口路径必须为绝对路径，不得包含父目录跳转或符号链接/junction/reparse point。CLI 只向标准输出写 JSON：正常完成索引返回 0；清单、路径、大小或读取稳定性不符合要求返回 2 和 `input_error`。返回 0 不等于证据完整或工程成功；缺文件、哈希漂移、身份冲突和无效 JSON 均在索引里如实报告。

## 最小清单

```json
{
  "schema": "chemical-observation-manifest-v1",
  "experiment_id": "experiment-a",
  "case_family_id": "family-a",
  "task_id": "task-a",
  "revision": "revision-1",
  "scenario_kind": "expected_refusal",
  "execution_mode": "offline_stub",
  "declared_resources": ["example-resource"],
  "observed_resources": null,
  "artifacts": [
    {
      "path": "run/summary.json",
      "role": "run_summary",
      "expected_sha256": "填写该文件的64位十六进制SHA256",
      "expected_identity": {
        "/run_id": "run-a",
        "/identity/task_id": "task-a"
      }
    }
  ]
}
```

示例中的 SHA256 必须替换成实际预期值。清单不能添加 `learning_eligible`、`source_approved` 等解禁字段；未知顶层或 artifact 字段直接拒绝。`role` 只是文件用途标签，不赋予任何可信级别。

| 字段 | 约束 |
|---|---|
| `experiment_id/case_family_id/task_id/revision` | 必填、非空字符串；最多 512 字符，保留类型，不将数字修订号隐式转换成字符串 |
| `scenario_kind` | `normal`、`expected_refusal`、`injected_fault`、`natural_failure` |
| `execution_mode` | `real_tool`、`offline_stub`、`text_only` |
| `declared_resources/observed_resources` | 可省略或为 null，表示未观察/未提供；显式空数组表示报告了空集合。最多 64 条非空字符串 |
| `artifacts` | 显式数组，最多 64 条，可为空；不会自动寻找其他文件 |
| `path` | evidence-root 内的 POSIX 相对路径；拒绝 `..`、`.`、反斜杠、盘符/ADS、重复分隔符、Windows 保留名、尾点/尾空格及大小写别名冲突 |
| `expected_sha256` | 必填 64 位十六进制哈希；大小写可接受，输出规范为小写 |
| `role` | 必填、非空标签，最多 128 字符 |
| `expected_identity` | 可选；键是下述有限字面指针，值是有界 JSON 标量；不得与清单上下文矛盾 |

资源列表仍是**清单报告的事实**，不是本工具独立捕获的调用。输出固定注明 `manifest_statement_not_independent_execution_proof`，不把声明成了“观察”就认定真实执行。

## JSON 提取与身份核对

只有扩展名为 `.json`、字节哈希相符、可解析为对象的文件才提取少量字段。其他类型仅关联哈希和字节数；哈希不符时不解析其中的状态。重复键、过深结构和非有限数值不作为可用 JSON 记录。

允许的身份字段为 `experiment_id`、`case_family_id`、`task_id`、`revision`、`case_id`、`run_id`、`execution_id`、`case_sha256`、`source_sha256`，位置仅限根字段或 `/identity/` 下的同名字段。因此合法指针例如 `/run_id`、`/identity/case_id`；任意数据指针、递归猜测和字段别名推断均不支持。

记录实际出现清单四个上下文字段时，工具自动逐一比对；根字段与 `/identity/` 字段同时出现时都检查，不能用其中一处正确值遮盖另一处冲突。`expected_identity` 增加明确期望，缺字段记录 `missing`。不按相近时间、文件名或相同目录推断同案。

`original_record` 仅包含以下原始投影，保留 0、false 和 null，不把不存在的值补成零：

- `schema_fields`：`/schema`、`/schema_version`。
- `identity_fields`：上述身份指针。
- `state_fields`：根字段 `status`、`ok`、`simulation_clean`、`delivery_passed`、`delivery_verified`、`strict_delivery_passed`、`engineering_passed`、`model_run_requested`、`source_unchanged`、`message_count`、`error_count`、`warning_count`、`native_created`、`native_executed`、`native_verified`，以及 `/run/status`。

非标量或超过 4096 字符的选中值只记录其省略位置，不展开任意载荷。原始投影中的 `engineering_passed: true` 等语句不是本工具的认可；工具不生成同名顶层结论，不以 `expected_refusal` 自动计工程成功。身份比较严格保留类型，例如 false 不等于 0。

## 输出状态

| 观察 | 输出 |
|---|---|
| 文件不存在 | `file_state=missing`，哈希和身份为 `unobserved`，没有伪造字节数或原字段 |
| 文件存在，预期哈希不同 | `hash_state=mismatch`、`json_state=not_parsed_hash_mismatch` |
| 哈希正确，但 JSON 无效 | `json_state=invalid`，不提取原字段 |
| 明确期望的身份字段未出现 | `identity_comparison.state=missing`；检查项没有伪造 observed 值 |
| 任一实际身份冲突 | `identity_comparison.state=conflict` |
| 已比较字段相符 | `matched_fields`，同时列 `unobserved_context_fields`；不认证完整同案或资格 |
| 无可比身份字段 | `unobserved` |

摘要只有清单数、读取数、缺失数、哈希/身份问题数、无效 JSON 数和实际读取字节数。它不是成功率、质量分数或第二个工程验收器。调用方仍须使用原 owner 的真实资格/质量检查；本工具不为任何消费者放行。

## 读取边界与验证

清单上限 128 KiB，单证据 1 MiB，总证据 8 MiB；JSON 深度最多 32、节点最多 50,000。所有路径先验证，读取文件时检查普通文件、前后身份与大小/修改时间，并在平台支持时使用不跟随链接的打开标志。拒绝检测到的路径漂移；这是应用层只读边界，不替代操作系统隔离。

运行新增合成测试：

```text
python -B -X utf8 tests/test_observation_index.py
```

测试覆盖串案、哈希漂移、缺失与未观察、原始零/布尔/null、来源字段不能解禁、资格回执不认证、预期拒绝的范围、只读且只开清单文件、路径逃逸/别名/普通文件/链接、Windows reparse 属性及大小限制。真实 symlink 创建若被宿主权限拒绝，会明确跳过；模拟 reparse 属性拒绝仍单独测试。测试不导入运行时或 COM，不包含真实项目输入。
