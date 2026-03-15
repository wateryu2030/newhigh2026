"""Tests for Alpha scoring."""

from evolution_engine import alpha_score, alpha_score_from_backtest_metrics, passes_alpha_threshold


def test_alpha_score_basic():
    s = alpha_score(
        sharpe_ratio=1.0, sortino_ratio=1.0, max_drawdown=0.05, win_rate_pct=55, profit_factor=1.5
    )
    assert 0 <= s <= 1


def test_alpha_score_from_metrics():
    metrics = {
        "sharpe_ratio": 0.5,
        "sortino_ratio": 0.6,
        "max_drawdown": 0.1,
        "win_rate_pct": 50,
        "profit_factor": 1.2,
    }
    s = alpha_score_from_backtest_metrics(metrics)
    assert 0 <= s <= 1


def test_passes_alpha_threshold():
    assert passes_alpha_threshold(0.6, threshold=0.5) is True
    assert passes_alpha_threshold(0.4, threshold=0.5) is False
