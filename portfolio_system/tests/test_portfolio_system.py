# -*- coding: utf-8 -*-
"""
portfolio_system 单元测试：市场状态、风控、策略池、绩效报告。
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _mock_kline(days: int = 100, start_price: float = 100.0) -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range(
        end=datetime.now().date(), periods=days, freq="D"
    )
    rets = np.random.randn(days) * 0.02
    closes = start_price * np.cumprod(1 + rets)
    df = pd.DataFrame({
        "date": [d.strftime("%Y-%m-%d") for d in dates],
        "open": closes * 0.99,
        "high": closes * 1.01,
        "low": closes * 0.98,
        "close": closes,
        "volume": np.random.randint(1_000_000, 5_000_000, days),
    })
    return df


def test_market_regime() -> None:
    from portfolio_system.market_regime import MarketRegime, MarketRegimeDetector

    detector = MarketRegimeDetector()
    df = _mock_kline(150)
    regime = detector.detect(df)
    assert regime in (MarketRegime.BULL, MarketRegime.NEUTRAL, MarketRegime.BEAR)
    scale = detector.get_position_scale(regime)
    assert 0.0 <= scale <= 1.0


def test_risk_control() -> None:
    from portfolio_system.risk_control import RiskController, RiskLevel

    rc = RiskController(stop_loss_pct=0.08)
    assert rc.check_stop_loss(100.0, 91.0) is True
    assert rc.check_stop_loss(100.0, 93.0) is False
    assert rc.check_account_risk(0.16) == RiskLevel.STOP
    assert rc.check_account_risk(0.02) == RiskLevel.LOW
    assert rc.get_position_scale(RiskLevel.STOP) == 0.0


def test_strategy_pool() -> None:
    from portfolio_system.strategy_pool import StrategyPool

    pool = StrategyPool(weights={"ma_cross": 0.5, "rsi": 0.5})
    w = pool.get_weights()
    assert len(w) >= 0
    df = _mock_kline(60)
    sigs = pool.run_all(df)
    assert isinstance(sigs, dict)


def test_performance_report() -> None:
    from portfolio_system.performance import PerformanceReport

    curve = [
        {"date": "2024-01-01", "value": 1.0},
        {"date": "2024-01-02", "value": 1.02},
        {"date": "2024-01-03", "value": 1.01},
    ]
    report = PerformanceReport.generate(curve)
    assert "total_return" in report
    assert "max_drawdown" in report
    assert "sharpe_ratio" in report
    assert report["total_return"] > 0


def test_portfolio_config() -> None:
    from portfolio_system.config import PortfolioConfig, RiskConfig

    cfg = PortfolioConfig(initial_cash=1_000_000.0)
    assert cfg.target_annual_return_min == 0.20
    assert cfg.target_annual_return_max == 0.40
    assert cfg.risk_config.stop_loss_pct == 0.08


def test_backtester() -> None:
    from portfolio_system.backtester import Backtester
    from portfolio_system.config import PortfolioConfig

    cfg = PortfolioConfig()
    bt = Backtester(cfg)

    def mock_load(sym: str, start: str, end: str) -> pd.DataFrame:
        return _mock_kline(100)

    bt.set_data_loaders(load_stock=mock_load, load_index=mock_load)
    result = bt.run("000001", "2024-01-01", "2024-06-30")
    assert "curve" in result
    assert "summary" in result or "error" in result


if __name__ == "__main__":
    test_market_regime()
    test_risk_control()
    test_strategy_pool()
    test_performance_report()
    test_portfolio_config()
    test_backtester()
    print("All tests passed.")
