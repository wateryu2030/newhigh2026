"""
统一将本仓库子包源码目录加入 sys.path。

当前布局为 ``scanner/src``（``market_scanner``）、``strategy/src``（``strategy_engine``）；
若仍存在旧目录名 ``market-scanner/src``、``strategy-engine/src`` 则兼容。
Gateway / system_runner / scripts 应通过本模块初始化路径，避免各文件硬编码不一致。
"""

from __future__ import annotations

import os
import sys

_STD_SRC = (
    "data-pipeline/src",
    "ai-models/src",
    "core/src",
)

# (首选, 兼容旧仓)
_SRC_ALIASES = (
    ("scanner/src", "market-scanner/src"),
    ("strategy/src", "strategy-engine/src"),
)

_OPTIONAL_SRC = (
    "backtest-engine/src",
    "ai-optimizer/src",
)


def repo_root() -> str:
    """本文件位于 system_core/，仓库根为其父目录。"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def prepend_repo_sources(root: str | None = None) -> str:
    """
    将子包 src 与仓库根插入 sys.path（根在最后插入的首位，便于 import system_core）。
    返回仓库根绝对路径。
    """
    r = os.path.abspath(root or repo_root())
    if r not in sys.path:
        sys.path.insert(0, r)
    for rel in _STD_SRC:
        p = os.path.join(r, rel)
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)
    for preferred, legacy in _SRC_ALIASES:
        chosen = None
        for rel in (preferred, legacy):
            p = os.path.join(r, rel)
            if os.path.isdir(p):
                chosen = p
                break
        if chosen and chosen not in sys.path:
            sys.path.insert(0, chosen)
    for rel in _OPTIONAL_SRC:
        p = os.path.join(r, rel)
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)
    return r
