# Optional Aspen MCP Invocation

MCP is an optional adapter, not a bundled Aspen capability. Continue through
the existing operations COM/runtime/evidence scripts when an MCP service is
absent; do not require installation merely to perform supported local work.

## Explicit local setup

Use a user-selected MCP provider whose license and current interface have been
reviewed. The complete distribution includes an optional MIT-licensed provider
under `vendor/aspen-mcp-toolkit/` and an offline launcher; this individual Skill
does not contain a second server. Configure the actual interpreter and arguments
through the host's supported settings. No credentials, Aspen license, machine
path or active server connection is preconfigured.

A configured server may offer open/run/get/set/close, block/stream editing or
export tools. Discover its real tool list, identify the exact provider/version,
and test only the smallest authorized operation. Historical tool names or
downloaded README examples are not proof the target machine supports them.

## Route and evidence

- Use a verified MCP adapter for bounded mechanical work within the frozen
  project authority; a tool's presence does not authorize mutations.
- Use the common runtime/supervisor for owned-session/timeout/lock handling.
- Preserve tool name, arguments, exact case identity, changed nodes, result
  state, paths/hashes, missing dependencies and close outcome.
- Final acceptance remains the shared strict Summary/history implementation
  plus current project/product/equipment gates on the exact candidate.
- Successful MCP prose does not prove current raw history is clean or that
  saved files reopen unchanged.

## Source boundary

Provider documentation, example parameters, optimization helpers and kinetics
presets are discovery aids only. User-supplied same-case evidence owns
quantities and source-to-card conversions. Use legally installed version-specific
Aspen help for card meanings. Do not merge third-party defaults or copied
commercial help into the public manual registry.

An installed provider, licensed Aspen runtime and local help data remain
execution prerequisites even when provider source and Python wheels are bundled.
If unavailable, report the exact unsupported operation; use the existing
COM/script path when it covers the authorized work.

## 原生分析与外部循环的区别

随包 provider 的 `sensitivity` 调用 `tools/sensitivity_advanced.py`，逐点
写值并重新运行，是外部参数扫描，不创建 Aspen 原生 SENSITIVITY 对象。
`linked_params` 只按固定倍率改参数，不会自动求解产品目标。其公开 `unit`
参数没有转交底层扫描实现；使用前须独立核对实际节点单位，不能据传参声称换算。

`get_value`、`set_value`、`explore` 和 `run_script` 是可用的底层通道，
不是已验证的原生 Calculator/Design Spec/Optimization 自动创建协议。
设置存在的节点不等于建立一个完整对象。按
[内置工具规则](../../aspen-document-driven-flowsheet/references/aspen_builtin_solve_fit_tools.md)
选工具，再经版本帮助、节点探测和真实导出核实执行；缺一个专用 MCP 方法不
代表 Aspen 没有该功能，也不自动授权用外部循环替代。
