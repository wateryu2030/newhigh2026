"""Tests for StrategyGene and multi_objective."""

from openclaw_engine.gene import StrategyGene
from openclaw_engine.multi_objective import composite_fitness, fitness_from_backtest_result


def test_gene_to_dict():
    g = StrategyGene(rule_tree={"and": []}, params={"position_pct": 0.1}, strategy_id="t1")
    d = g.to_dict()
    assert d["strategy_id"] == "t1"
    assert d["params"]["position_pct"] == 0.1


def test_gene_from_dict():
    d = {"strategy_id": "t2", "rule_tree": {}, "params": {}}
    g = StrategyGene.from_dict(d)
    assert g.strategy_id == "t2"


def test_composite_fitness():
    f = composite_fitness(total_return=0.1, sharpe_ratio=1.0, max_drawdown=-0.05)
    assert f != 0
    f2 = composite_fitness(total_return=None, sharpe_ratio=None)
    assert f2 == 0.0


def test_fitness_from_backtest_result():
    r = {"total_return": 0.2, "sharpe_ratio": 1.5, "max_drawdown": -0.1}
    f = fitness_from_backtest_result(r, use_composite=True)
    assert f != 0
    f2 = fitness_from_backtest_result(r, use_composite=False)
    assert f2 == 1.5
