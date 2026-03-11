"""Tests for strategy pool."""
from evolution_engine import StrategyPool, StrategyRecord, StrategyStatus


def test_pool_add_get():
    pool = StrategyPool()
    r = StrategyRecord("s1", "test", "trend_following", {"fast": 10}, ["BTCUSDT"], StrategyStatus.CANDIDATE)
    pool.add(r)
    assert pool.get("s1") is not None
    assert pool.get("s1").name == "test"
    assert pool.get("s2") is None


def test_pool_list_by_status():
    pool = StrategyPool()
    pool.add(StrategyRecord("a", "A", "tf", {}, [], StrategyStatus.LIVE))
    pool.add(StrategyRecord("b", "B", "mr", {}, [], StrategyStatus.CANDIDATE))
    assert len(pool.list_live()) == 1
    assert len(pool.list_candidates()) == 1
