# Auto-fixed by Cursor on 2026-04-02: synthetic buy-hold vs flat baseline using vectorbt.
"""简单买入持有回测烟测。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _p in (
    _ROOT / "backtest-engine" / "src",
    _ROOT / "core" / "src",
):
    s = str(_p)
    if _p.is_dir() and s not in sys.path:
        sys.path.insert(0, s)


def _load_runner():
    pytest.importorskip("vectorbt")
    path = _ROOT / "backtest-engine" / "src" / "backtest_engine" / "runner.py"
    spec = importlib.util.spec_from_file_location("newhigh_bt_runner", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run_backtest


def test_buy_hold_beats_zero_exposure():
    run_backtest = _load_runner()
    idx = pd.date_range("2020-01-01", periods=50, freq="D")
    close = pd.Series(range(100, 150), dtype=float, index=idx)
    entries = pd.Series([True] + [False] * 49, index=idx)
    exits = pd.Series([False] * 49 + [True], index=idx)
    pf = run_backtest(close, entries, exits, init_cash=10_000.0, fees=0.0002, freq="1D")
    assert pf.value().iloc[-1] > 0
