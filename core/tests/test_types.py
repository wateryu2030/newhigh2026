"""Tests for core types."""
from datetime import datetime

import pytest

from core import OHLCV, Signal


def test_signal_enum():
    assert Signal.BUY.value == "BUY"
    assert Signal.SELL.value == "SELL"
    assert Signal.HOLD.value == "HOLD"


def test_ohlcv_to_dict():
    ts = datetime(2025, 1, 1, 12, 0, 0)
    bar = OHLCV("BTCUSDT", ts, 100.0, 101.0, 99.0, 100.5, 1000.0, "1h")
    d = bar.to_dict()
    assert d["symbol"] == "BTCUSDT"
    assert d["open"] == 100.0
    assert d["close"] == 100.5
    assert d["interval"] == "1h"
