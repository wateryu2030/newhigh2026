"""Shared types for the AI hedge fund platform."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class Signal(str, Enum):
    """Trading signal."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class OHLCV:
    """Normalized OHLCV bar."""

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    interval: str  # 1m, 5m, 1h, 1d

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "interval": self.interval,
        }


@dataclass
class Position:
    """Position info."""

    symbol: str
    side: str  # LONG, SHORT
    quantity: float
    entry_price: float
    unrealized_pnl: Optional[float] = None
