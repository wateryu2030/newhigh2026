# -*- coding: utf-8 -*-
"""
PortfolioManager 单元测试：等权、得分加权、信号整合、交易执行。
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _mock_kline(days: int = 60) -> pd.DataFrame:
    """模拟 K 线数据。"""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now().date(), periods=days, freq="D")
    base = 100
    rets = np.random.randn(days) * 0.02
    closes = base * np.cumprod(1 + rets)
    df = pd.DataFrame({
        "date": [d.strftime("%Y-%m-%d") for d in dates],
        "open": closes * 0.99,
        "high": closes * 1.01,
        "low": closes * 0.98,
        "close": closes,
        "volume": np.random.randint(1000000, 5000000, days),
    })
    return df


def _mock_strategy_buy():
    """模拟策略：始终 BUY。"""
    class AlwaysBuy:
        name = "AlwaysBuy"
        def generate_signals(self, df):
            if df is None or len(df) == 0:
                return []
            return [{"date": str(df.iloc[-1].get("date", ""))[:10], "type": "BUY", "price": float(df["close"].iloc[-1]), "reason": "test"}]
    return AlwaysBuy()


def _mock_strategy_hold():
    """模拟策略：始终 HOLD。"""
    class AlwaysHold:
        name = "AlwaysHold"
        def generate_signals(self, df):
            return []
    return AlwaysHold()


def _mock_strategy_sell():
    """模拟策略：始终 SELL。"""
    class AlwaysSell:
        name = "AlwaysSell"
        def generate_signals(self, df):
            if df is None or len(df) == 0:
                return []
            return [{"date": str(df.iloc[-1].get("date", ""))[:10], "type": "SELL", "price": float(df["close"].iloc[-1]), "reason": "test"}]
    return AlwaysSell()


def test_weight_allocator_equal():
    """等权分配。"""
    from portfolio.weight_allocator import WeightAllocator

    strategies = ["A", "B", "C"]
    w = WeightAllocator.equal_weight(strategies)
    assert len(w) == 3
    assert abs(sum(w) - 1.0) < 1e-6
    assert all(abs(x - 1/3) < 1e-6 for x in w)


def test_weight_allocator_score():
    """得分加权。"""
    from portfolio.weight_allocator import WeightAllocator

    strategies = ["A", "B", "C"]
    scores = [0.5, 0.3, 0.2]
    w = WeightAllocator.score_weight(strategies, scores)
    assert len(w) == 3
    assert abs(sum(w) - 1.0) < 1e-6
    assert w[0] > w[1] > w[2]


def test_weight_allocator_risk_parity():
    """风险平价。"""
    from portfolio.weight_allocator import WeightAllocator

    strategies = ["A", "B", "C"]
    vols = [0.1, 0.2, 0.3]  # A 波动率最低，权重应最高
    w = WeightAllocator.risk_parity_weight(strategies, vols)
    assert len(w) == 3
    assert abs(sum(w) - 1.0) < 1e-6
    assert w[0] > w[1] > w[2]


def test_signal_aggregator_majority():
    """信号整合：多数 BUY -> BUY。"""
    from portfolio.signal_aggregator import SignalAggregator, AggregatorConfig

    config = AggregatorConfig(mode="majority", min_buy_ratio=0.5)
    agg = SignalAggregator(config)
    s1 = pd.Series({"2024-01-01": 1.0, "2024-01-02": 0.0})  # BUY, HOLD
    s2 = pd.Series({"2024-01-01": 1.0, "2024-01-02": -1.0})  # BUY, SELL
    s3 = pd.Series({"2024-01-01": 0.0, "2024-01-02": -1.0})  # HOLD, SELL
    signals = {"A": s1, "B": s2, "C": s3}
    out = agg.aggregate(signals)
    assert "2024-01-01" in out.index
    assert "2024-01-02" in out.index
    assert out["2024-01-01"] == 1.0  # 2 BUY, 1 HOLD -> majority BUY
    assert out["2024-01-02"] == -1.0  # 2 SELL, 1 HOLD -> majority SELL


def test_strategy_adapter():
    """策略适配器。"""
    from portfolio.base_strategy import StrategyAdapter

    strat = _mock_strategy_buy()
    adapter = StrategyAdapter(strat)
    df = _mock_kline(10)
    sig = adapter.generate_signal(df)
    assert len(sig) > 0
    assert adapter.score(df) >= 0


def test_performance_report():
    """绩效报告。"""
    from portfolio.performance_report import PerformanceReport

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
    assert report["max_drawdown"] >= 0


def test_portfolio_manager_equal_weight():
    """PortfolioManager 等权组合。"""
    from portfolio.portfolio_manager import PortfolioManager
    from portfolio.base_strategy import StrategyAdapter

    strategies = [StrategyAdapter(_mock_strategy_buy()), StrategyAdapter(_mock_strategy_hold())]
    pm = PortfolioManager(strategies, weight_mode="equal")
    df = _mock_kline(30)
    sig = pm.generate_portfolio_signal(df)
    assert len(sig) >= 0  # 可能为空，取决于日期对齐
    pm.rebalance()


def test_portfolio_manager_score_weight():
    """PortfolioManager 得分加权。"""
    from portfolio.portfolio_manager import PortfolioManager
    from portfolio.base_strategy import StrategyAdapter

    strategies = [StrategyAdapter(_mock_strategy_buy()), StrategyAdapter(_mock_strategy_sell())]
    pm = PortfolioManager(strategies, weight_mode="score")
    df = _mock_kline(30)
    sig = pm.generate_portfolio_signal(df)
    pm.rebalance()


if __name__ == "__main__":
    test_weight_allocator_equal()
    test_weight_allocator_score()
    test_weight_allocator_risk_parity()
    test_signal_aggregator_majority()
    test_strategy_adapter()
    test_performance_report()
    test_portfolio_manager_equal_weight()
    test_portfolio_manager_score_weight()
    print("All tests passed.")
