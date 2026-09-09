# Agent 协议 1.6 混合流程夹具

- `protocol_1_6_hybrid_prepare_request.json`：可直接运行的 `hybrid_prepare` 请求。
- `protocol_1_6_hybrid_run_no_llm_request.json`：可直接运行的无 LLM `hybrid_run` 请求。
- `generate_protocol_1_6_hybrid_fixtures.py`：重跑确定性输入，生成带当前
  `prepared_sha256`、`context_sha256` 和 `orchestration_sha256` 的严格
  `hybrid_continue` 与离线 mock `hybrid_run` 夹具，并核对两条路径得到相同编排哈希。

只校验、不写文件：

```powershell
python app\fixtures\generate_protocol_1_6_hybrid_fixtures.py
```

物化本机当前版本的 prepared、step output、continue/run 请求与响应：

```powershell
python app\fixtures\generate_protocol_1_6_hybrid_fixtures.py --output-dir outputs\protocol_1_6_fixtures
```

`prepared` 绑定当前确定性引擎结果、知识上下文和本机证据路径，不能作为跨版本、
跨机器的永久常量。算法、图谱或路径变化后必须重新运行生成器；禁止手工改哈希。
