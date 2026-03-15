from alpha_scoring import alpha_score, score_backtest_results, rank_and_select_top


def test_alpha_score():
    s = alpha_score(sharpe_ratio=1.0, max_drawdown=0.05, total_return=0.1)
    assert 0 <= s <= 1


def test_rank_and_select_top():
    strategies_with_metrics = [
        ({"id": "a"}, {"sharpe_ratio": 0.5, "max_drawdown": 0.1}),
        ({"id": "b"}, {"sharpe_ratio": 1.5, "max_drawdown": 0.05}),
    ]
    top = rank_and_select_top(strategies_with_metrics, top_fraction=0.5)
    assert len(top) >= 1
    assert top[0][1] >= top[-1][1]
