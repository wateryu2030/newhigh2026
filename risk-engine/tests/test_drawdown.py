"""Tests for drawdown control."""

from risk_engine import (
    current_drawdown,
    max_drawdown,
    drawdown_ok,
    should_disable_strategy_drawdown,
)


def test_current_drawdown():
    # Equity 100 -> 80 -> current 20% dd
    assert current_drawdown([100, 90, 80]) == 0.2
    assert current_drawdown([100, 110]) == 0.0


def test_max_drawdown():
    assert max_drawdown([100, 90, 80, 85, 70]) == 0.3


def test_drawdown_ok():
    assert drawdown_ok([100, 95], max_drawdown_pct=0.1) is True
    assert drawdown_ok([100, 80], max_drawdown_pct=0.1) is False
