"""执行模式：simulated | live，供 Gateway 与执行层统一读取。"""
from __future__ import annotations

import os
from typing import Optional

from .base import BaseBroker
from .simulated_broker import SimulatedBroker
from .live_broker import LiveBroker

_MODE: Optional[str] = None


def execution_mode() -> str:
    """当前执行模式：simulated（模拟）或 live（实盘）。"""
    global _MODE
    if _MODE is not None:
        return _MODE
    return os.environ.get("EXECUTION_MODE", "simulated").lower()


def set_execution_mode(mode: str) -> None:
    global _MODE
    _MODE = (mode or "simulated").lower()


def get_broker() -> BaseBroker:
    """根据 execution_mode() 返回 SimulatedBroker 或 LiveBroker。"""
    if execution_mode() == "live":
        return LiveBroker()
    return SimulatedBroker()
