# 统一交易接口：模拟盘 / 实盘（券商）抽象
from .base import BaseBroker, OrderResult, PositionInfo
from .simulated_broker import SimulatedBroker
from .live_broker import LiveBroker
from .registry import get_broker, execution_mode, set_execution_mode

__all__ = [
    "BaseBroker",
    "OrderResult",
    "PositionInfo",
    "SimulatedBroker",
    "LiveBroker",
    "get_broker",
    "execution_mode",
    "set_execution_mode",
]
