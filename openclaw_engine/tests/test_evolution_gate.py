"""strategy_market 入库门槛环境变量。"""

import os

from openclaw_engine.evolution_orchestrator import passes_strategy_market_gate


def test_gate_permissive_when_env_unset():
    os.environ.pop("OPENCLAW_MIN_SHARPE", None)
    os.environ.pop("OPENCLAW_MAX_DRAWDOWN_ABS", None)
    assert passes_strategy_market_gate({"sharpe_ratio": None, "max_drawdown": None}) is True


def test_min_sharpe_env():
    os.environ["OPENCLAW_MIN_SHARPE"] = "1.0"
    try:
        assert passes_strategy_market_gate({"sharpe_ratio": 1.5}) is True
        assert passes_strategy_market_gate({"sharpe_ratio": 0.5}) is False
        assert passes_strategy_market_gate({"sharpe_ratio": None}) is False
    finally:
        os.environ.pop("OPENCLAW_MIN_SHARPE", None)


def test_max_drawdown_abs_env():
    os.environ["OPENCLAW_MAX_DRAWDOWN_ABS"] = "0.25"
    try:
        assert passes_strategy_market_gate({"max_drawdown": -0.1}) is True
        assert passes_strategy_market_gate({"max_drawdown": -0.5}) is False
    finally:
        os.environ.pop("OPENCLAW_MAX_DRAWDOWN_ABS", None)
