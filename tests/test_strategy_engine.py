"""Integration tests for strategy engine and backtest portfolio."""

import pytest


def test_backtest_allocator_import():
    from backtest_engine import allocate_weights

    out = allocate_weights(["s1", "s2"], [0.6, 0.4])
    assert len(out) == 2
    assert out[0][0] == "s1" and abs(out[0][1] - 0.6) < 1e-6
    assert out[1][0] == "s2" and abs(out[1][1] - 0.4) < 1e-6


def test_backtest_allocator_equal_weight():
    from backtest_engine import allocate_weights

    out = allocate_weights(["a", "b", "c"])
    assert len(out) == 3
    for _, w in out:
        assert abs(w - 1 / 3) < 1e-6


def test_run_portfolio_backtest_empty_strategies():
    """空 strategy_ids 应返回 error。"""
    from backtest_engine import run_portfolio_backtest

    r = run_portfolio_backtest(strategy_ids=[], start_date="2024-01-01", end_date="2024-12-31")
    assert "error" in r
    assert r["error"] == "no_strategy_ids"
