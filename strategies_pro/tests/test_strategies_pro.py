# -*- coding: utf-8 -*-
"""
strategies_pro 单元测试：每策略可运行、信号格式正确、权重分配合理。
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _mock_ohlcv(days: int = 100, start_price: float = 100.0, symbol: str = "000001.XSHE") -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now().date(), periods=days, freq="D")
    rets = np.random.randn(days) * 0.02
    close = start_price * np.cumprod(1 + rets)
    high = close * (1 + np.abs(np.random.randn(days) * 0.01))
    low = close * (1 - np.abs(np.random.randn(days) * 0.01))
    df = pd.DataFrame({
        "date": [d.strftime("%Y-%m-%d") for d in dates],
        "open": close * 0.99,
        "high": high,
        "low": low,
        "close": close,
        "volume": np.random.randint(1_000_000, 5_000_000, days),
    })
    return df


def _mock_market_data(n_symbols: int = 3) -> dict:
    symbols = [f"00000{i}.XSHE" for i in range(1, n_symbols + 1)]
    return {s: _mock_ohlcv(80, 100.0, s) for s in symbols}


def test_trend_breakout() -> None:
    from strategies_pro import TrendBreakoutStrategy

    s = TrendBreakoutStrategy(ma_short=20, ma_long=60)
    data = _mock_market_data(3)
    stocks = s.select_stocks(data)
    assert isinstance(stocks, list)
    sigs = s.generate_signals(data)
    assert isinstance(sigs, pd.DataFrame)
    if len(sigs) > 0:
        assert "symbol" in sigs.columns and "signal" in sigs.columns
        assert "weight" in sigs.columns
        assert sigs["weight"].sum() <= 0.5


def test_strong_pullback() -> None:
    from strategies_pro import StrongPullbackStrategy

    s = StrongPullbackStrategy(lookback=30)
    data = _mock_market_data(3)
    stocks = s.select_stocks(data)
    assert isinstance(stocks, list)
    sigs = s.generate_signals(data)
    assert isinstance(sigs, pd.DataFrame)
    if len(sigs) > 0:
        assert "symbol" in sigs.columns and "signal" in sigs.columns


def test_etf_rotation() -> None:
    from strategies_pro import ETFRotationStrategy

    s = ETFRotationStrategy(momentum_days=20)
    data = {"510300.XSHG": _mock_ohlcv(50), "510500.XSHG": _mock_ohlcv(50)}
    stocks = s.select_stocks(data)
    assert isinstance(stocks, list)
    sigs = s.generate_signals(data)
    assert isinstance(sigs, pd.DataFrame)
    if len(sigs) > 0:
        assert "symbol" in sigs.columns and sigs["signal"].iloc[0] in ("BUY", "SELL")


def test_market_regime() -> None:
    from strategies_pro import MarketRegime, MarketRegimeDetector

    det = MarketRegimeDetector()
    df = _mock_ohlcv(100)
    regime = det.detect(df)
    assert regime in (MarketRegime.BULL, MarketRegime.NEUTRAL, MarketRegime.BEAR)
    tw, sw, ew = det.get_strategy_weights(regime)
    assert 0 <= tw <= 1 and 0 <= sw <= 1 and 0 <= ew <= 1


def test_strategy_scorer() -> None:
    from strategies_pro import StrategyScorer

    sc = StrategyScorer()
    score = sc.score(recent_return=0.1, max_drawdown=0.05, sharpe_ratio=1.0, win_rate=0.6)
    assert 0 <= score <= 1
    curve = [{"date": "2024-01-01", "value": 1.0}, {"date": "2024-06-01", "value": 1.15}]
    s2 = sc.score_from_curve(curve)
    assert 0 <= s2 <= 1


def test_strategy_manager() -> None:
    from strategies_pro import StrategyManager

    data = _mock_market_data(3)
    manager = StrategyManager()
    combined = manager.get_combined_signals(data)
    assert isinstance(combined, pd.DataFrame)
    if len(combined) > 0:
        assert "symbol" in combined.columns and "weight" in combined.columns
        assert "strategy" in combined.columns
        assert combined["weight"].sum() <= 1.5


if __name__ == "__main__":
    test_trend_breakout()
    test_strong_pullback()
    test_etf_rotation()
    test_market_regime()
    test_strategy_scorer()
    test_strategy_manager()
    print("All tests passed.")
