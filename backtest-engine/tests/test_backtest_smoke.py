"""冒烟测试：backtest_engine 包可导入且核心 API 存在。"""


def test_backtest_engine_import():
    """包可导入且包含预期导出。"""
    import backtest_engine

    assert hasattr(backtest_engine, "run_backtest")
    assert hasattr(backtest_engine, "run_backtest_from_ohlcv")
    assert hasattr(backtest_engine, "compute_metrics")
    assert hasattr(backtest_engine, "load_ohlcv_from_db")
