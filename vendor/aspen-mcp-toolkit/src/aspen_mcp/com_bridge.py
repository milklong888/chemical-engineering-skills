"""COM 桥接 — 向后兼容壳。

实际实现在 bridge/ 子包中。此模块保留 aspen 全局单例，
确保所有现有 tools/*.py 的 import 不受影响。
"""

from __future__ import annotations

import sys

if sys.platform == "win32":
    from .bridge.windows import WindowsBridge as _BridgeClass
else:
    from .bridge.stub import StubBridge as _BridgeClass

aspen = _BridgeClass()
