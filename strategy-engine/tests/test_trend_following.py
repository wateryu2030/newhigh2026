"""Tests for trend following strategy."""
from datetime import datetime, timezone

from core import OHLCV
from strategy_engine import trend_following_signals, trend_following_entries_exits


def test_trend_following_signals():
    # Minimal series: 60 bars so we have slow_period=50
    base = 100.0
    ohlcv = [
        OHLCV("BTC", datetime.now(timezone.utc), base + i * 0.1, base + i * 0.1 + 1, base + i * 0.1 - 1, base + i * 0.1, 1000.0, "1h")
        for i in range(60)
    ]
    signals = trend_following_signals(ohlcv, fast_period=5, slow_period=20)
    assert len(signals) == 60


def test_trend_following_entries_exits():
    ohlcv = [
        OHLCV("BTC", datetime.now(timezone.utc), 100.0, 101.0, 99.0, 100.0, 1000.0, "1h")
        for _ in range(55)
    ]
    entries, exits = trend_following_entries_exits(ohlcv, fast_period=5, slow_period=20)
    assert len(entries) == 55 and len(exits) == 55
