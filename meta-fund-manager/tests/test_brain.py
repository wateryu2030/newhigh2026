from meta_fund_manager import select_strategies, allocate_capital, should_disable, monitor_performance

def test_select_strategies():
    scored = [({"id": f"s{i}"}, 0.3 + i * 0.05) for i in range(10)]
    sel = select_strategies(scored, max_strategies=3, min_score=0.4)
    assert len(sel) <= 3

def test_allocate_capital():
    strategies = [1, 2, 3]
    alloc = allocate_capital(strategies, 1000.0, method="equal")
    assert sum(alloc.values()) == 1000.0

def test_should_disable():
    assert should_disable("s1", 0.15, 0) is True
    assert should_disable("s1", 0.05, 0.01) is False
