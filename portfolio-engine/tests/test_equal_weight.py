"""Tests for equal weight allocation."""

from portfolio_engine import equal_weight_weights, equal_weight_position_sizes


def test_equal_weight_weights():
    w = equal_weight_weights(["A", "B", "C"])
    assert len(w) == 3
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert w["A"] == w["B"] == w["C"]


def test_equal_weight_position_sizes():
    sizes = equal_weight_position_sizes(["A", "B"], capital=1000.0)
    assert sizes["A"] == 500.0
    assert sizes["B"] == 500.0
