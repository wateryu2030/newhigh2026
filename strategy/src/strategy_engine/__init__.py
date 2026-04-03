# strategy-engine
from core import Signal
from .base_strategy import BaseStrategy, prevent_future_data
from .trend_following import trend_following_signals, trend_following_entries_exits
from .mean_reversion import mean_reversion_signals, mean_reversion_entries_exits
from .breakout import breakout_signals, breakout_entries_exits

__all__ = [
    "Signal",
    "BaseStrategy",
    "prevent_future_data",
    "trend_following_signals",
    "trend_following_entries_exits",
    "mean_reversion_signals",
    "mean_reversion_entries_exits",
    "breakout_signals",
    "breakout_entries_exits",
]
