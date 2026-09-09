# 可移植回归测试

四个测试入口保留原有函数和断言，默认不启动 Aspen。运行时测试使用假 COM 对象以及真实 Python 子进程测试锁与超时；学习准入和前向测试使用明确标注的合成任务、关闭事件、提案和观测，不构成用户授权或工程事实。

入口为 `aspen-document-driven-flowsheet/scripts/tests/test_learning_admission_cli.py`、`aspen-plus-operations/scripts/tests/test_aspen_runtime.py`、`chemical-engineering-expert/scripts/test_learning_eligibility.py` 以及本目录的 `test_evolution_candidate.py`。从安装后的技能目录执行对应 Python 文件；前向测试加 `--with-cli` 才包含真实命令行链路。

每个入口接受 `--artifact-root OUTPUT`，记录只写入该输出目录；未指定时生成独立临时目录。学习类测试通过 `release_test_support.py` 实际执行随包解析器单元测试、诊断探针和两份保全的真实表格格式摘录，生成当前代码的验证记录。该记录只证明解析器代码行为，不证明模拟计算或流程交付通过；摘录中的非零错误和警告仍必须被识别。

两项原回归分别依赖外部已有失败模拟摘要、旧版事件索引。默认仅跳过这两项，其他通用反例仍执行。可用 `--external-evidence-profile PROFILE.json` 明确提供下列合同；文件路径可相对配置文件，所有 SHA256 必须匹配。未知合同或哈希漂移是失败，不会当成跳过。

```json
{
  "schema": "chemical-skill-external-regression-profile-v1",
  "artifacts": {
    "failed_simulation_receipt": {
      "path": "external/failed_summary.json",
      "sha256": "REPLACE_WITH_ACTUAL_FILE_SHA256",
      "evidence_class": "external_existing_evidence"
    },
    "legacy_error_index": {
      "path": "external/legacy_index.json",
      "sha256": "REPLACE_WITH_ACTUAL_FILE_SHA256",
      "evidence_class": "external_existing_evidence"
    }
  }
}
```

这份示意配置不是证据，包内不附私有模拟摘要或事件索引，也不以合成文件冒充它们。外部测试仅读取给定文件，不修改源证据。
