# Offline backend runtime

The upstream source and documentation remain unchanged. `SOURCE_MANIFEST.json`
lists their hashes and the original tool names. `offline-runtime.lock.json`
freezes the audited CPython 3.14 / Windows AMD64 dependency wheels. The wheels
are distributed separately with the offline release, not as copied virtual
environments. Keep the license files inside all wheels and the upstream LICENSE.

Install only into a new directory:

```text
python tools/install_offline_runtime.py --wheelhouse <wheelhouse> --target <new-venv>
```

The installer rejects existing targets, missing or altered wheels, unknown
lock formats and incompatible Python platforms. It does not modify global MCP
configuration, start Aspen or prove a simulation is valid. Missing packages are
reported; there is no network fallback.

For the optional workspace-retrieval NumPy runtime, keep the original 70-wheel
lock unchanged and add the separately bound extension to a **new** environment:

```text
python tools/install_offline_runtime.py --wheelhouse <wheelhouse> --target <new-venv> --extension-lock vendor/aspen-mcp-toolkit/numpy-retrieval-extension.lock.json --extension-wheelhouse <wheelhouse>/extensions/numpy
```

The extension pins NumPy 2.4.6 for CPython 3.14 / Windows AMD64. It cannot
override any base distribution. The NumPy wheel retains its bundled license
files, including notices for incorporated components. Installing this extension
does not by itself create a knowledge index or validate retrieval quality.

Use the new environment's Python to run this directory's `run_offline_mcp.py`.
This small launcher sets the package path, disables FastMCP's default update
check and banner, and reads no dotenv file. The vendored server source remains
unchanged. The transport is stdio.
Do not assume `status` and `probe` are harmless discovery calls: on Windows they
can connect to Aspen. Use initialize and tools/list for protocol discovery.

The process-level network/COM-blocked test is provided by
`tests/test_mcp_offline.py --integration --runtime <new-venv> --output <new-output>`.
It checks real SDK initialization and all tool schemas without opening Aspen.
Windows asyncio's own verified socketpair self-wakeup IPC is the only permitted
socket connection; external sockets, general loopback connections and DNS are
blocked in both Python test processes. No system firewall is changed.
The only callable knowledge check is source-verified local text lookup; it does
not validate engineering recommendations. Protocol success is separate from
mechanical Aspen operation, strict simulation evidence and engineering delivery.

No desktop application, Aspen installation, commercial license or GUI package
is included here. The original service exposes some GUI/model-writing tools;
exposure is not permission to call them. The maintenance directory is never a
startup dependency.
