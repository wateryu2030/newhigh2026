"""Strategy generator: LLM-based strategy discovery (stub: returns config dict)."""
from typing import Any, Dict, List, Optional


def generate_strategy(
    description: Optional[str] = None,
    symbols: Optional[List[str]] = None,
    constraints: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate strategy config from description (LLM placeholder).
    Returns dict: strategy_type (trend_following | mean_reversion | breakout),
    params (e.g. fast_period, slow_period), name.
    """
    # Stub: return a default trend_following config. In production, call LLM to propose params.
    return {
        "name": "generated_trend_following",
        "strategy_type": "trend_following",
        "params": {
            "fast_period": 10,
            "slow_period": 50,
        },
        "symbols": symbols or ["BTCUSDT"],
    }


def generate_strategies_batch(
    count: int = 5,
    strategy_types: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Generate multiple strategy configs (e.g. for evolution)."""
    types = strategy_types or ["trend_following", "mean_reversion", "breakout"]
    results = []
    for i, st in enumerate(types[:count]):
        results.append({
            "name": f"generated_{st}_{i}",
            "strategy_type": st,
            "params": _default_params(st),
            "symbols": ["BTCUSDT"],
        })
    return results


def _default_params(strategy_type: str) -> Dict[str, Any]:
    if strategy_type == "trend_following":
        return {"fast_period": 10, "slow_period": 50}
    if strategy_type == "mean_reversion":
        return {"rsi_period": 14, "oversold": 30, "overbought": 70}
    if strategy_type == "breakout":
        return {"lookback": 20}
    return {}
