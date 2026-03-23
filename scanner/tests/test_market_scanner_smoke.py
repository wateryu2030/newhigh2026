"""冒烟测试：market_scanner 包可导入且核心 API 存在。"""


def test_market_scanner_import():
    """包可导入且包含预期导出。"""
    import market_scanner

    assert hasattr(market_scanner, "run_limit_up_scanner")
    assert hasattr(market_scanner, "run_fund_flow_scanner")
    assert hasattr(market_scanner, "run_trend_scanner")
    assert hasattr(market_scanner, "run_sniper")
