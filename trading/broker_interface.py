# -*- coding: utf-8 -*-
"""
券商接口：机构层统一入口，委托 backend.trading.Broker。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

try:
    from backend.trading.broker_interface import Broker as _Broker
except ImportError:
    _Broker = None


def Broker(mode: str = "simulation") -> Any:
    """返回券商实例。mode: simulation | live。"""
    if _Broker is None:
        return None
    return _Broker(mode=mode)
