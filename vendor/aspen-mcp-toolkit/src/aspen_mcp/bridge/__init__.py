"""桥工厂：根据平台返回合适的 AspenBridge 实现。

Windows → WindowsBridge（真实 COM）
其他平台 → StubBridge（纯内存模拟）
"""

from __future__ import annotations

import sys


def make_bridge():
    """返回当前平台可用的桥实现。"""
    if sys.platform == "win32":
        from .windows import WindowsBridge
        return WindowsBridge()
    from .stub import StubBridge
    return StubBridge()
