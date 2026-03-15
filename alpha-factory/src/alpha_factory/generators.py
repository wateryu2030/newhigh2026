"""
Alpha Factory — 策略工厂
Generate large numbers of trading strategy candidates: LLM stub, genetic, random indicator combinations.
"""

import random
from typing import Any, Dict, List

# Indicator combinations and rule templates
INDICATORS = ["rsi", "macd", "vwap", "atr", "momentum", "volatility"]
STRATEGY_TYPES = ["trend_following", "mean_reversion", "breakout"]
TIMEFRAMES = ["1m", "5m", "1h", "1d"]


def _random_params(strategy_type: str) -> Dict[str, Any]:
    if strategy_type == "trend_following":
        return {
            "fast_period": random.randint(5, 30),
            "slow_period": random.randint(30, 120),
        }
    if strategy_type == "mean_reversion":
        return {
            "rsi_period": random.randint(7, 21),
            "oversold": random.uniform(20, 40),
            "overbought": random.uniform(60, 80),
        }
    if strategy_type == "breakout":
        return {"lookback": random.randint(10, 50)}
    return {}


def generate_random_combination() -> Dict[str, Any]:
    """Generate one strategy candidate from random indicator combinations and thresholds."""
    strategy_type = random.choice(STRATEGY_TYPES)
    indicators = random.sample(INDICATORS, k=min(random.randint(1, 3), len(INDICATORS)))
    return {
        "strategy_type": strategy_type,
        "params": _random_params(strategy_type),
        "indicators": indicators,
        "timeframe": random.choice(TIMEFRAMES),
        "entry_exit_rules": f"{'+'.join(indicators)}",
    }


def generate_population(size: int = 100) -> List[Dict[str, Any]]:
    """Generate a population of strategy candidates."""
    return [generate_random_combination() for _ in range(size)]


def generate_llm_strategy(description: str = "") -> Dict[str, Any]:
    """LLM-based strategy generation (stub: returns a default candidate)."""
    return {
        "strategy_type": "trend_following",
        "params": {"fast_period": 10, "slow_period": 50},
        "indicators": ["rsi", "macd"],
        "timeframe": "1h",
        "entry_exit_rules": "RSI+MACD",
        "source": "llm",
    }


def generate_indicator_rules() -> List[Dict[str, Any]]:
    """Generate candidates from fixed indicator rule templates. E.g. RSI<30 buy, RSI>70 sell."""
    candidates = []
    for st in STRATEGY_TYPES:
        for _ in range(5):
            candidates.append(
                {
                    "strategy_type": st,
                    "params": _random_params(st),
                    "indicators": ["rsi"],
                    "timeframe": random.choice(TIMEFRAMES),
                    "entry_exit_rules": "RSI_threshold",
                }
            )
    return candidates
