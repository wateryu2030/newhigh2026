# strategy-engine
from core import Signal
from .trend_following import trend_following_signals, trend_following_entries_exits
from .mean_reversion import mean_reversion_signals, mean_reversion_entries_exits
from .breakout import breakout_signals, breakout_entries_exits

__all__ = [
    "Signal",
    "trend_following_signals",
    "trend_following_entries_exits",
    "mean_reversion_signals",
    "mean_reversion_entries_exits",
    "breakout_signals",
    "breakout_entries_exits",
]
